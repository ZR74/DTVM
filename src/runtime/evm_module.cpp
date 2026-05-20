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
    Mod->ShouldFallbackToInterp =
        FallbackJITSuitability || FallbackDynamicReturn ||
        FallbackDeepEntryMutation || FallbackHiddenPrefixLoopMerge;
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
