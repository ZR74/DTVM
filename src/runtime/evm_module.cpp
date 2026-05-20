// Copyright (C) 2025 the DTVM authors. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

#include "runtime/evm_module.h"

#include "action/compiler.h"
#include "action/evm_module_loader.h"
#include "common/enums.h"
#include "common/errors.h"
#include "runtime/codeholder.h"
#include "runtime/symbol_wrapper.h"
#include "utils/statistics.h"
#include "utils/wasm.h"

#include <memory>
#include <string>

#include "compiler/evm_frontend/evm_analyzer.h"

#ifdef ZEN_ENABLE_MULTIPASS_JIT
#include "compiler/evm_compiler.h"
#endif

namespace zen::runtime {

namespace {

bool hasUnresolvedCompatibleDynamicReturnTrampoline(
    const COMPILER::EVMAnalyzer &Analyzer) {
  for (const auto &[EntryPC, Info] : Analyzer.getBlockInfos()) {
    if (!Info.HasDynamicJump) {
      continue;
    }
    if (Analyzer.getOutgoingCompatibleDynamicJumpShapeClassForBlock(EntryPC) ==
        0) {
      continue;
    }
    if (!Analyzer
             .canTransferCompatibleDynamicJumpTargetsWithoutRuntimeMaterialization(
                 EntryPC)) {
      return true;
    }
  }
  return false;
}

bool hasUnresolvedNonLiftedDeepEntryMutationRisk(
    const COMPILER::EVMAnalyzer &Analyzer) {
  for (const auto &[EntryPC, Info] : Analyzer.getBlockInfos()) {
    (void)EntryPC;
    if (Info.CanLiftStack || Info.ResolvedEntryStackDepth >= 0) {
      continue;
    }
    bool HasBackedgePred = false;
    for (uint64_t PredPC : Info.Predecessors) {
      if (PredPC >= EntryPC) {
        HasBackedgePred = true;
        break;
      }
    }
    if (!HasBackedgePred) {
      continue;
    }
    const int32_t PreloadedSuffixDepth = -Info.MinPopHeight;
    const int32_t MaxTouchedEntryDepth =
        Info.EntryStackDepth + Info.MaxStackHeight;
    if (MaxTouchedEntryDepth > PreloadedSuffixDepth) {
      return true;
    }
  }
  return false;
}

bool hasNonLiftedHiddenPrefixLoopMergeRisk(
    const COMPILER::EVMAnalyzer &Analyzer) {
  for (const auto &[EntryPC, Info] : Analyzer.getBlockInfos()) {
    if (Info.CanLiftStack || Info.HiddenLiveInPrefixDepth <= 0 ||
        Info.Predecessors.size() < 2) {
      continue;
    }
    for (uint64_t PredPC : Info.Predecessors) {
      if (PredPC >= EntryPC) {
        return true;
      }
    }
  }

  for (const auto &[EntryPC, Info] : Analyzer.getBlockInfos()) {
    for (uint64_t SuccPC : Info.Successors) {
      if (SuccPC > EntryPC) {
        continue;
      }
      auto TargetIt = Analyzer.getBlockInfos().find(SuccPC);
      if (TargetIt == Analyzer.getBlockInfos().end()) {
        continue;
      }
      const auto &TargetInfo = TargetIt->second;
      if (!TargetInfo.CanLiftStack && TargetInfo.HiddenLiveInPrefixDepth > 0) {
        return true;
      }
    }
  }

  return false;
}

bool hasUndefinedInstructionRisk(const COMPILER::EVMAnalyzer &Analyzer) {
  for (const auto &[EntryPC, Info] : Analyzer.getBlockInfos()) {
    (void)EntryPC;
    if (Info.HasUndefinedInstr) {
      return true;
    }
  }
  return false;
}

bool isGasSensitiveLoopOpcode(evmc_opcode Opcode) {
  switch (Opcode) {
  case OP_GAS:
  case OP_MLOAD:
  case OP_MSTORE:
  case OP_MSTORE8:
  case OP_MCOPY:
  case OP_SSTORE:
  case OP_TSTORE:
  case OP_CALL:
  case OP_CALLCODE:
  case OP_DELEGATECALL:
  case OP_STATICCALL:
  case OP_CREATE:
  case OP_CREATE2:
  case OP_SELFDESTRUCT:
  case OP_REVERT:
    return true;
  default:
    return false;
  }
}

bool hasGasSensitiveLoopRisk(const COMPILER::EVMAnalyzer &Analyzer,
                             const uint8_t *Bytecode, size_t BytecodeSize) {
  for (const auto &[EntryPC, Info] : Analyzer.getBlockInfos()) {
    bool HasBackedgePred = false;
    for (uint64_t PredPC : Info.Predecessors) {
      if (PredPC >= EntryPC) {
        HasBackedgePred = true;
        break;
      }
    }
    if (!HasBackedgePred) {
      continue;
    }

    const uint64_t BodyStart = Info.BodyStartPC;
    const uint64_t BodyEnd = std::min<uint64_t>(Info.BodyEndPC, BytecodeSize);
    for (uint64_t PC = BodyStart; PC < BodyEnd; ++PC) {
      evmc_opcode Opcode = static_cast<evmc_opcode>(Bytecode[PC]);
      if (isGasSensitiveLoopOpcode(Opcode)) {
        return true;
      }
      if (Opcode >= OP_PUSH1 && Opcode <= OP_PUSH32) {
        PC +=
            static_cast<uint64_t>(Opcode) - static_cast<uint64_t>(OP_PUSH1) + 1;
      }
    }
  }
  return false;
}

bool hasMemoryCarriedControlRisk(const uint8_t *Bytecode, size_t BytecodeSize) {
  bool HasMload = false;
  bool HasMstore = false;
  bool HasJumpi = false;

  for (size_t PC = 0; PC < BytecodeSize; ++PC) {
    evmc_opcode Opcode = static_cast<evmc_opcode>(Bytecode[PC]);
    if (Opcode == OP_MLOAD) {
      HasMload = true;
    } else if (Opcode == OP_MSTORE || Opcode == OP_MSTORE8) {
      HasMstore = true;
    } else if (Opcode == OP_JUMPI) {
      HasJumpi = true;
    }

    if (HasMload && HasMstore && HasJumpi) {
      return true;
    }

    if (Opcode >= OP_PUSH1 && Opcode <= OP_PUSH32) {
      PC += static_cast<size_t>(Opcode) - static_cast<size_t>(OP_PUSH1) + 1;
    }
  }

  return false;
}

bool hasConsecutiveJumpdestControlRisk(const uint8_t *Bytecode,
                                       size_t BytecodeSize) {
  bool HasJumpControl = false;
  bool HasConsecutiveJumpdest = false;

  for (size_t PC = 0; PC < BytecodeSize; ++PC) {
    evmc_opcode Opcode = static_cast<evmc_opcode>(Bytecode[PC]);
    if (Opcode == OP_JUMP || Opcode == OP_JUMPI) {
      HasJumpControl = true;
    } else if (Opcode == OP_JUMPDEST && PC + 1 < BytecodeSize &&
               Bytecode[PC + 1] == OP_JUMPDEST) {
      HasConsecutiveJumpdest = true;
    }

    if (HasJumpControl && HasConsecutiveJumpdest) {
      return true;
    }

    if (Opcode >= OP_PUSH1 && Opcode <= OP_PUSH32) {
      PC += static_cast<size_t>(Opcode) - static_cast<size_t>(OP_PUSH1) + 1;
    }
  }

  return false;
}

} // namespace

EVMModule::EVMModule(Runtime *RT)
    : BaseModule(RT, ModuleType::EVM), Code(nullptr), CodeSize(0) {
  // do nothing
}

EVMModule::~EVMModule() {
  if (Name) {
    this->freeSymbol(Name);
    Name = common::WASM_SYMBOL_NULL;
  }

  if (Code) {
    deallocate(Code);
  }
}

EVMModuleUniquePtr
EVMModule::newEVMModule(Runtime &RT, CodeHolderUniquePtr CodeHolder,
                        evmc_revision Rev,
                        EVMMemorySpecializationProfile MemoryProfile) {
  void *ObjBuf = RT.allocate(sizeof(EVMModule));
  ZEN_ASSERT(ObjBuf);

  auto *RawMod = new (ObjBuf) EVMModule(&RT);
  EVMModuleUniquePtr Mod(RawMod);
  Mod->setRevision(Rev);
  Mod->setMemorySpecializationProfile(MemoryProfile);

  const uint8_t *Data = static_cast<const uint8_t *>(CodeHolder->getData());
  size_t CodeSize = CodeHolder->getSize();

  action::EVMModuleLoader Loader(*Mod, reinterpret_cast<const Byte *>(Data),
                                 CodeSize);

  auto &Stats = RT.getStatistics();
  auto Timer = Stats.startRecord(utils::StatisticPhase::Load);

  Loader.load();

  Stats.stopRecord(Timer);

  Mod->CodeHolder = std::move(CodeHolder);

  ZEN_ASSERT(RT.getEVMHost());
  Mod->Host = RT.getEVMHost();

  if (RT.getConfig().Mode != common::RunMode::InterpMode) {
    // Run the EVMAnalyzer once at module creation to determine if this
    // contract should fall back to interpreter. This avoids per-call O(n)
    // bytecode scans in the execute() hot path.
    COMPILER::EVMAnalyzer Analyzer(Rev);
    Analyzer.analyze(reinterpret_cast<const uint8_t *>(Mod->Code),
                     Mod->CodeSize);
    const bool FallbackJITSuitability =
        Analyzer.getJITSuitability().ShouldFallback;
    const bool FallbackDynamicReturn =
        hasUnresolvedCompatibleDynamicReturnTrampoline(Analyzer);
    const bool FallbackDeepEntryMutation =
        hasUnresolvedNonLiftedDeepEntryMutationRisk(Analyzer);
    const bool FallbackHiddenPrefixLoopMerge =
        hasNonLiftedHiddenPrefixLoopMergeRisk(Analyzer);
    const bool FallbackUndefinedInstr = hasUndefinedInstructionRisk(Analyzer);
    const bool FallbackGasSensitiveLoop = hasGasSensitiveLoopRisk(
        Analyzer, reinterpret_cast<const uint8_t *>(Mod->Code), Mod->CodeSize);
    const bool FallbackMemoryCarriedControl = hasMemoryCarriedControlRisk(
        reinterpret_cast<const uint8_t *>(Mod->Code), Mod->CodeSize);
    const bool FallbackConsecutiveJumpdestControl =
        hasConsecutiveJumpdestControlRisk(
            reinterpret_cast<const uint8_t *>(Mod->Code), Mod->CodeSize);
    Mod->ShouldFallbackToInterp =
        FallbackJITSuitability || FallbackDynamicReturn ||
        FallbackDeepEntryMutation || FallbackHiddenPrefixLoopMerge ||
        FallbackUndefinedInstr || FallbackGasSensitiveLoop ||
        FallbackMemoryCarriedControl || FallbackConsecutiveJumpdestControl;
    if (!Mod->ShouldFallbackToInterp) {
      // JIT is about to compile this module — mark the bytecode cache so the
      // SPP metering pipeline runs on first access.
      Mod->CacheNeedsSPP = true;
      action::performEVMJITCompile(*Mod);
    }
  }

  return Mod;
}

const evm::EVMBytecodeCache &EVMModule::getBytecodeCache() const {
  if (!BytecodeCacheInitialized) {
    initBytecodeCache();
    BytecodeCacheInitialized = true;
  }
  return BytecodeCache;
}

void EVMModule::initBytecodeCache() const {
  evm::buildBytecodeCache(BytecodeCache, Code, CodeSize, Revision,
                          CacheNeedsSPP);
}

} // namespace zen::runtime
