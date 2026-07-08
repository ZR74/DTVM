// Copyright (C) 2026 the DTVM authors. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

#ifndef COMPILER_EVM_FRONTEND_EVM_MEMORY_FACTS_H
#define COMPILER_EVM_FRONTEND_EVM_MEMORY_FACTS_H

#include "evmc/evmc.h"
#include "evmc/instructions.h"

#include <cstdint>
#include <limits>
#include <utility>
#include <vector>

namespace COMPILER {

// Fact: address space separates independent byte-addressed domains before any
// alias analysis exists. Phase 0 records it; later phases may query it.
enum class AddressSpace : uint8_t {
  Memory,
  CallData,
  Code,
  ReturnData,
  ExternalCode,
  Storage,
  TransientStorage,
  Unknown
};

// Fact: MVP address expression. It intentionally supports only
// Base+ConstOffset.
enum class AddressBaseKind : uint8_t { Const, StackValue, Unknown };

struct AddressExpr {
  AddressBaseKind Kind = AddressBaseKind::Unknown;
  uint64_t Const = 0;
  uint32_t ValueId = 0;
  int64_t Offset = 0;
  bool Exact = false;

  static AddressExpr unknown() { return {}; }

  static AddressExpr constant(uint64_t Value) {
    AddressExpr Expr;
    Expr.Kind = AddressBaseKind::Const;
    Expr.Const = 0;
    Expr.Offset = static_cast<int64_t>(Value);
    Expr.Exact =
        Value <= static_cast<uint64_t>(std::numeric_limits<int64_t>::max());
    return Expr;
  }

  static AddressExpr stackValue(uint32_t ValueId, int64_t Offset = 0) {
    AddressExpr Expr;
    Expr.Kind = AddressBaseKind::StackValue;
    Expr.ValueId = ValueId;
    Expr.Offset = Offset;
    Expr.Exact = true;
    return Expr;
  }

  bool isKnown() const { return Kind != AddressBaseKind::Unknown && Exact; }
};

// Fact: MVP size expression. Unknown symbolic sizes are deliberately not
// represented in Phase 0.
struct SizeExpr {
  bool Known = false;
  uint64_t Value = 0;

  static SizeExpr unknown() { return {}; }
  static SizeExpr constant(uint64_t Value) { return {true, Value}; }
};

// Fact: a byte interval in an address space. Empty ranges are explicit because
// EVM memory expansion treats size=0 specially.
struct MemoryInterval {
  AddressSpace Space = AddressSpace::Unknown;
  AddressExpr Addr;
  SizeExpr Size;
  bool Empty = false;
};

enum class MemoryEffect : uint8_t {
  None,
  Read,
  Write,
  ReadWrite,
  Escape,
  MemorySizeObserver,
  GasSensitive,
  Unknown
};

enum class MemoryOpKind : uint8_t {
  MLoad,
  MStore,
  MStore8,
  MCopy,
  CallDataLoad,
  CallDataCopy,
  CodeCopy,
  ReturnDataCopy,
  ExtCodeCopy,
  Keccak,
  Log,
  Return,
  Revert,
  Call,
  Create,
  MSize,
  Gas,
  Other
};

// Fact: the single core memory access model. It records what the bytecode does,
// not whether anything can be optimized.
struct MemoryOp {
  uint32_t Id = 0;
  uint64_t Pc = 0;
  evmc_opcode Opcode = OP_STOP;
  MemoryOpKind Kind = MemoryOpKind::Other;
  std::vector<MemoryInterval> Reads;
  std::vector<MemoryInterval> Writes;
  MemoryEffect Effect = MemoryEffect::None;
  bool IsTerminator = false;
};

struct MemoryFacts {
  std::vector<MemoryOp> Ops;

  void clear() { Ops.clear(); }
  bool empty() const { return Ops.empty(); }
  size_t size() const { return Ops.size(); }
};

// Fact builder: consumes bytecode order and builds MemoryFacts. It has no
// dependency on MIR builder, analysis, or optimization consumers.
class MemoryFactsBuilder {
public:
  MemoryFactsBuilder() = default;

  void reset() {
    Facts.clear();
    Stack.clear();
    NextValueId = 1;
  }

  void beginBlock(uint64_t EntryPC, uint32_t EntryDepth) {
    (void)EntryPC;
    Stack.clear();
    for (uint32_t I = 0; I < EntryDepth; ++I) {
      Stack.push_back(makeUnknownValue());
    }
  }

  void observeOpcode(evmc_opcode Opcode, uint64_t Pc, const uint8_t *Bytecode,
                     size_t BytecodeSize) {
    if (Opcode >= OP_PUSH0 && Opcode <= OP_PUSH32) {
      observePush(Opcode, Pc, Bytecode, BytecodeSize);
      return;
    }
    if (Opcode >= OP_DUP1 && Opcode <= OP_DUP16) {
      duplicate(static_cast<uint32_t>(Opcode - OP_DUP1 + 1));
      return;
    }
    if (Opcode >= OP_SWAP1 && Opcode <= OP_SWAP16) {
      swap(static_cast<uint32_t>(Opcode - OP_SWAP1 + 1));
      return;
    }
    if (Opcode >= OP_LOG0 && Opcode <= OP_LOG4) {
      observeLog(Opcode, Pc);
      return;
    }

    switch (Opcode) {
    case OP_ADD:
      observeAdd();
      return;
    case OP_SUB:
      observeSub();
      return;
    case OP_POP:
      (void)pop();
      return;
    case OP_MLOAD:
      observeMLoad(Pc);
      return;
    case OP_MSTORE:
      observeMStore(Pc);
      return;
    case OP_MSTORE8:
      observeMStore8(Pc);
      return;
    case OP_MCOPY:
      observeMCopy(Pc);
      return;
    case OP_KECCAK256:
      observeKeccak(Pc);
      return;
    case OP_CALLDATALOAD:
      observeCallDataLoad(Pc);
      return;
    case OP_CALLDATACOPY:
      observeCopy(Pc, Opcode, MemoryOpKind::CallDataCopy,
                  AddressSpace::CallData);
      return;
    case OP_CODECOPY:
      observeCopy(Pc, Opcode, MemoryOpKind::CodeCopy, AddressSpace::Code);
      return;
    case OP_RETURNDATACOPY:
      observeCopy(Pc, Opcode, MemoryOpKind::ReturnDataCopy,
                  AddressSpace::ReturnData);
      return;
    case OP_EXTCODECOPY:
      observeExtCodeCopy(Pc);
      return;
    case OP_RETURN:
      observeReturnLike(Pc, Opcode, MemoryOpKind::Return);
      return;
    case OP_REVERT:
      observeReturnLike(Pc, Opcode, MemoryOpKind::Revert);
      return;
    case OP_CALL:
    case OP_CALLCODE:
      observeCall(Pc, Opcode, true);
      return;
    case OP_DELEGATECALL:
    case OP_STATICCALL:
      observeCall(Pc, Opcode, false);
      return;
    case OP_CREATE:
      observeCreate(Pc, Opcode, false);
      return;
    case OP_CREATE2:
      observeCreate(Pc, Opcode, true);
      return;
    case OP_MSIZE:
      addOp(Pc, Opcode, MemoryOpKind::MSize, MemoryEffect::MemorySizeObserver);
      pushUnknown();
      return;
    case OP_GAS:
      addOp(Pc, Opcode, MemoryOpKind::Gas, MemoryEffect::GasSensitive);
      pushUnknown();
      return;
    default:
      observeGenericOpcode(Opcode);
      return;
    }
  }

  const MemoryFacts &getFacts() const { return Facts; }
  MemoryFacts takeFacts() { return std::move(Facts); }

private:
  struct StackValue {
    bool ConstKnown = false;
    uint64_t ConstValue = 0;
    uint32_t ValueId = 0;
    bool HasAddress = false;
    AddressExpr Address;
  };

  static constexpr uint32_t InvalidValueId = 0;

  MemoryFacts Facts;
  std::vector<StackValue> Stack;
  uint32_t NextValueId = 1;

  StackValue makeUnknownValue() {
    StackValue Value;
    Value.ValueId = NextValueId++;
    return Value;
  }

  StackValue makeConstValue(uint64_t ConstValue) {
    StackValue Value;
    Value.ConstKnown = true;
    Value.ConstValue = ConstValue;
    Value.HasAddress = true;
    Value.Address = AddressExpr::constant(ConstValue);
    return Value;
  }

  void pushUnknown() { Stack.push_back(makeUnknownValue()); }
  void pushValue(const StackValue &Value) { Stack.push_back(Value); }

  StackValue pop() {
    if (Stack.empty()) {
      return makeUnknownValue();
    }
    StackValue Value = Stack.back();
    Stack.pop_back();
    return Value;
  }

  StackValue peek(uint32_t IndexFromTop) const {
    if (Stack.size() <= IndexFromTop) {
      StackValue Unknown;
      return Unknown;
    }
    return Stack[Stack.size() - IndexFromTop - 1];
  }

  void duplicate(uint32_t IndexFromTopOneBased) {
    pushValue(peek(IndexFromTopOneBased - 1));
  }

  void swap(uint32_t IndexFromTop) {
    if (Stack.size() <= IndexFromTop) {
      return;
    }
    std::swap(Stack.back(), Stack[Stack.size() - IndexFromTop - 1]);
  }

  bool addSignedOffset(const AddressExpr &Base, int64_t Delta,
                       AddressExpr &Out) const {
    if (!Base.isKnown()) {
      return false;
    }
    if ((Delta > 0 &&
         Base.Offset > std::numeric_limits<int64_t>::max() - Delta) ||
        (Delta < 0 &&
         Base.Offset < std::numeric_limits<int64_t>::min() - Delta)) {
      return false;
    }
    Out = Base;
    Out.Offset += Delta;
    return true;
  }

  bool constToI64(uint64_t Value, int64_t &Out) const {
    if (Value > static_cast<uint64_t>(std::numeric_limits<int64_t>::max())) {
      return false;
    }
    Out = static_cast<int64_t>(Value);
    return true;
  }

  AddressExpr addressFromValue(const StackValue &Value) const {
    if (Value.HasAddress && Value.Address.isKnown()) {
      return Value.Address;
    }
    if (Value.ConstKnown) {
      return AddressExpr::constant(Value.ConstValue);
    }
    if (Value.ValueId != InvalidValueId) {
      return AddressExpr::stackValue(Value.ValueId);
    }
    return AddressExpr::unknown();
  }

  SizeExpr sizeFromValue(const StackValue &Value) const {
    if (Value.ConstKnown) {
      return SizeExpr::constant(Value.ConstValue);
    }
    return SizeExpr::unknown();
  }

  MemoryInterval interval(AddressSpace Space, const StackValue &Addr,
                          const StackValue &Size) const {
    SizeExpr SizeValue = sizeFromValue(Size);
    MemoryInterval Result{Space, addressFromValue(Addr), SizeValue, false};
    Result.Empty = SizeValue.Known && SizeValue.Value == 0;
    return Result;
  }

  MemoryInterval fixedInterval(AddressSpace Space, const StackValue &Addr,
                               uint64_t Size) const {
    return MemoryInterval{Space, addressFromValue(Addr),
                          SizeExpr::constant(Size), Size == 0};
  }

  MemoryOp &addOp(uint64_t Pc, evmc_opcode Opcode, MemoryOpKind Kind,
                  MemoryEffect Effect) {
    MemoryOp Op;
    Op.Id = static_cast<uint32_t>(Facts.Ops.size());
    Op.Pc = Pc;
    Op.Opcode = Opcode;
    Op.Kind = Kind;
    Op.Effect = Effect;
    Facts.Ops.push_back(std::move(Op));
    return Facts.Ops.back();
  }

  void observePush(evmc_opcode Opcode, uint64_t Pc, const uint8_t *Bytecode,
                   size_t BytecodeSize) {
    const uint8_t NumBytes = static_cast<uint8_t>(Opcode - OP_PUSH0);
    if (NumBytes == 0) {
      pushValue(makeConstValue(0));
      return;
    }
    if (NumBytes > 8 || Pc + 1 + NumBytes > BytecodeSize) {
      pushUnknown();
      return;
    }
    uint64_t Value = 0;
    for (uint8_t I = 0; I < NumBytes; ++I) {
      Value = (Value << 8) | Bytecode[Pc + 1 + I];
    }
    pushValue(makeConstValue(Value));
  }

  void observeAdd() {
    StackValue A = pop();
    StackValue B = pop();
    if (A.ConstKnown && B.ConstKnown) {
      pushValue(makeConstValue(A.ConstValue + B.ConstValue));
      return;
    }

    StackValue Result = makeUnknownValue();
    int64_t Delta = 0;
    AddressExpr Expr;
    if (A.ConstKnown && constToI64(A.ConstValue, Delta) &&
        addSignedOffset(addressFromValue(B), Delta, Expr)) {
      Result.HasAddress = true;
      Result.Address = Expr;
    } else if (B.ConstKnown && constToI64(B.ConstValue, Delta) &&
               addSignedOffset(addressFromValue(A), Delta, Expr)) {
      Result.HasAddress = true;
      Result.Address = Expr;
    }
    pushValue(Result);
  }

  void observeSub() {
    StackValue Subtrahend = pop();
    StackValue Minuend = pop();
    if (Subtrahend.ConstKnown && Minuend.ConstKnown) {
      pushValue(makeConstValue(Minuend.ConstValue - Subtrahend.ConstValue));
      return;
    }

    StackValue Result = makeUnknownValue();
    int64_t Delta = 0;
    AddressExpr Expr;
    if (Subtrahend.ConstKnown && constToI64(Subtrahend.ConstValue, Delta) &&
        addSignedOffset(addressFromValue(Minuend), -Delta, Expr)) {
      Result.HasAddress = true;
      Result.Address = Expr;
    }
    pushValue(Result);
  }

  void observeMLoad(uint64_t Pc) {
    StackValue Addr = pop();
    MemoryOp &Op = addOp(Pc, OP_MLOAD, MemoryOpKind::MLoad, MemoryEffect::Read);
    Op.Reads.push_back(fixedInterval(AddressSpace::Memory, Addr, 32));
    pushUnknown();
  }

  void observeMStore(uint64_t Pc) {
    StackValue Addr = pop();
    (void)pop(); // value
    MemoryOp &Op =
        addOp(Pc, OP_MSTORE, MemoryOpKind::MStore, MemoryEffect::Write);
    Op.Writes.push_back(fixedInterval(AddressSpace::Memory, Addr, 32));
  }

  void observeMStore8(uint64_t Pc) {
    StackValue Addr = pop();
    (void)pop(); // value
    MemoryOp &Op =
        addOp(Pc, OP_MSTORE8, MemoryOpKind::MStore8, MemoryEffect::Write);
    Op.Writes.push_back(fixedInterval(AddressSpace::Memory, Addr, 1));
  }

  void observeMCopy(uint64_t Pc) {
    StackValue Dest = pop();
    StackValue Src = pop();
    StackValue Size = pop();
    MemoryOp &Op =
        addOp(Pc, OP_MCOPY, MemoryOpKind::MCopy, MemoryEffect::ReadWrite);
    Op.Reads.push_back(interval(AddressSpace::Memory, Src, Size));
    Op.Writes.push_back(interval(AddressSpace::Memory, Dest, Size));
  }

  void observeKeccak(uint64_t Pc) {
    StackValue Offset = pop();
    StackValue Size = pop();
    MemoryOp &Op =
        addOp(Pc, OP_KECCAK256, MemoryOpKind::Keccak, MemoryEffect::Read);
    Op.Reads.push_back(interval(AddressSpace::Memory, Offset, Size));
    pushUnknown();
  }

  void observeLog(evmc_opcode Opcode, uint64_t Pc) {
    StackValue Offset = pop();
    StackValue Size = pop();
    const uint8_t NumTopics = static_cast<uint8_t>(Opcode - OP_LOG0);
    for (uint8_t I = 0; I < NumTopics; ++I) {
      (void)pop();
    }
    MemoryOp &Op = addOp(Pc, Opcode, MemoryOpKind::Log, MemoryEffect::Read);
    Op.Reads.push_back(interval(AddressSpace::Memory, Offset, Size));
  }

  void observeCallDataLoad(uint64_t Pc) {
    StackValue Offset = pop();
    MemoryOp &Op = addOp(Pc, OP_CALLDATALOAD, MemoryOpKind::CallDataLoad,
                         MemoryEffect::Read);
    Op.Reads.push_back(fixedInterval(AddressSpace::CallData, Offset, 32));
    pushUnknown();
  }

  void observeCopy(uint64_t Pc, evmc_opcode Opcode, MemoryOpKind Kind,
                   AddressSpace SourceSpace) {
    StackValue DestOffset = pop();
    StackValue Offset = pop();
    StackValue Size = pop();
    MemoryOp &Op = addOp(Pc, Opcode, Kind, MemoryEffect::ReadWrite);
    Op.Reads.push_back(interval(SourceSpace, Offset, Size));
    Op.Writes.push_back(interval(AddressSpace::Memory, DestOffset, Size));
  }

  void observeExtCodeCopy(uint64_t Pc) {
    (void)pop(); // address
    StackValue DestOffset = pop();
    StackValue Offset = pop();
    StackValue Size = pop();
    MemoryOp &Op = addOp(Pc, OP_EXTCODECOPY, MemoryOpKind::ExtCodeCopy,
                         MemoryEffect::ReadWrite);
    Op.Reads.push_back(interval(AddressSpace::ExternalCode, Offset, Size));
    Op.Writes.push_back(interval(AddressSpace::Memory, DestOffset, Size));
  }

  void observeReturnLike(uint64_t Pc, evmc_opcode Opcode, MemoryOpKind Kind) {
    StackValue Offset = pop();
    StackValue Size = pop();
    MemoryOp &Op = addOp(Pc, Opcode, Kind, MemoryEffect::Escape);
    Op.Reads.push_back(interval(AddressSpace::Memory, Offset, Size));
    Op.IsTerminator = true;
  }

  void observeCall(uint64_t Pc, evmc_opcode Opcode, bool HasValue) {
    (void)pop(); // gas
    (void)pop(); // to
    if (HasValue) {
      (void)pop();
    }
    StackValue ArgsOffset = pop();
    StackValue ArgsSize = pop();
    StackValue RetOffset = pop();
    StackValue RetSize = pop();
    MemoryOp &Op = addOp(Pc, Opcode, MemoryOpKind::Call, MemoryEffect::Unknown);
    Op.Reads.push_back(interval(AddressSpace::Memory, ArgsOffset, ArgsSize));
    Op.Writes.push_back(interval(AddressSpace::Memory, RetOffset, RetSize));
    pushUnknown();
  }

  void observeCreate(uint64_t Pc, evmc_opcode Opcode, bool HasSalt) {
    (void)pop(); // value
    StackValue Offset = pop();
    StackValue Size = pop();
    if (HasSalt) {
      (void)pop();
    }
    MemoryOp &Op =
        addOp(Pc, Opcode, MemoryOpKind::Create, MemoryEffect::Escape);
    Op.Reads.push_back(interval(AddressSpace::Memory, Offset, Size));
    pushUnknown();
  }

  void observeGenericOpcode(evmc_opcode Opcode) {
    const auto &Metrics = evmc_get_instruction_metrics_table(EVMC_CANCUN);
    const auto &Metric = Metrics[static_cast<uint8_t>(Opcode)];
    const int PopCount = Metric.stack_height_required;
    const int PushCount = PopCount + Metric.stack_height_change;
    for (int I = 0; I < PopCount; ++I) {
      (void)pop();
    }
    for (int I = 0; I < PushCount; ++I) {
      pushUnknown();
    }
  }
};

} // namespace COMPILER

#endif // COMPILER_EVM_FRONTEND_EVM_MEMORY_FACTS_H
