// Copyright (C) 2026 the DTVM authors. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

#ifndef COMPILER_EVM_FRONTEND_EVM_MEMORY_ANALYSIS_H
#define COMPILER_EVM_FRONTEND_EVM_MEMORY_ANALYSIS_H

#include "compiler/evm_frontend/evm_memory_facts.h"

#include <cstdint>
#include <limits>
#include <optional>

namespace COMPILER {

// Inference: normalized memory barrier category for a MemoryOp. This is not a
// lowering decision; consumers decide how to use the barrier.
enum class MemoryBarrierKind : uint8_t {
  None,
  Read,
  Write,
  ReadWrite,
  Escape,
  MemorySizeObserver,
  GasSensitive,
  Unknown
};

// Inference: MVP alias lattice. Phase 1 intentionally exposes only NoAlias and
// MayAlias. MustAlias and PartialAlias are future extensions.
enum class MemoryAliasResult : uint8_t { NoAlias, MayAlias };

enum class IntervalRelationKind : uint8_t { Unknown, Disjoint, Equal, Overlap };

// Inference: derives a relation between two MemoryIntervals from Facts only.
// It proves relations for exact Base+ConstOffset intervals and otherwise
// returns Unknown.
class IntervalRelation {
public:
  static IntervalRelationKind compare(const MemoryInterval &LHS,
                                      const MemoryInterval &RHS) {
    if (LHS.Empty || RHS.Empty) {
      return IntervalRelationKind::Disjoint;
    }
    if (LHS.Space != RHS.Space) {
      if (LHS.Space == AddressSpace::Unknown ||
          RHS.Space == AddressSpace::Unknown) {
        return IntervalRelationKind::Unknown;
      }
      return IntervalRelationKind::Disjoint;
    }

    std::optional<Bounds> LHSBounds = getBounds(LHS);
    std::optional<Bounds> RHSBounds = getBounds(RHS);
    if (!LHSBounds || !RHSBounds || !sameBase(*LHSBounds, *RHSBounds)) {
      return IntervalRelationKind::Unknown;
    }

    if (LHSBounds->End <= RHSBounds->Begin ||
        RHSBounds->End <= LHSBounds->Begin) {
      return IntervalRelationKind::Disjoint;
    }
    if (LHSBounds->Begin == RHSBounds->Begin &&
        LHSBounds->End == RHSBounds->End) {
      return IntervalRelationKind::Equal;
    }
    return IntervalRelationKind::Overlap;
  }

  static bool isKnownDisjoint(const MemoryInterval &LHS,
                              const MemoryInterval &RHS) {
    return compare(LHS, RHS) == IntervalRelationKind::Disjoint;
  }

private:
  struct Bounds {
    AddressBaseKind BaseKind = AddressBaseKind::Unknown;
    uint64_t Const = 0;
    uint32_t ValueId = 0;
    int64_t Begin = 0;
    int64_t End = 0;
  };

  static std::optional<Bounds> getBounds(const MemoryInterval &Interval) {
    if (!Interval.Addr.isKnown() || !Interval.Size.Known) {
      return std::nullopt;
    }
    if (Interval.Addr.Offset < 0) {
      return std::nullopt;
    }
    if (Interval.Size.Value >
        static_cast<uint64_t>(std::numeric_limits<int64_t>::max())) {
      return std::nullopt;
    }

    const int64_t Size = static_cast<int64_t>(Interval.Size.Value);
    const int64_t Begin = Interval.Addr.Offset;
    if (Begin > std::numeric_limits<int64_t>::max() - Size) {
      return std::nullopt;
    }

    Bounds Result;
    Result.BaseKind = Interval.Addr.Kind;
    Result.Const = Interval.Addr.Const;
    Result.ValueId = Interval.Addr.ValueId;
    Result.Begin = Begin;
    Result.End = Begin + Size;
    return Result;
  }

  static bool sameBase(const Bounds &LHS, const Bounds &RHS) {
    if (LHS.BaseKind != RHS.BaseKind) {
      return false;
    }
    switch (LHS.BaseKind) {
    case AddressBaseKind::Const:
      return LHS.Const == RHS.Const;
    case AddressBaseKind::StackValue:
      return LHS.ValueId == RHS.ValueId;
    case AddressBaseKind::Unknown:
      return false;
    }
    return false;
  }
};

// Inference: classifies each MemoryOp as a barrier. It only consumes
// MemoryFacts and never emits MIR or runtime helpers.
class BarrierAnalysis {
public:
  explicit BarrierAnalysis(const MemoryFacts &Facts) : Facts(Facts) {}

  MemoryBarrierKind getBarrierKind(const MemoryOp &Op) const {
    switch (Op.Effect) {
    case MemoryEffect::None:
      break;
    case MemoryEffect::Read:
      return MemoryBarrierKind::Read;
    case MemoryEffect::Write:
      return MemoryBarrierKind::Write;
    case MemoryEffect::ReadWrite:
      return MemoryBarrierKind::ReadWrite;
    case MemoryEffect::Escape:
      return MemoryBarrierKind::Escape;
    case MemoryEffect::MemorySizeObserver:
      return MemoryBarrierKind::MemorySizeObserver;
    case MemoryEffect::GasSensitive:
      return MemoryBarrierKind::GasSensitive;
    case MemoryEffect::Unknown:
      return MemoryBarrierKind::Unknown;
    }

    const bool HasReads = !Op.Reads.empty();
    const bool HasWrites = !Op.Writes.empty();
    if (HasReads && HasWrites) {
      return MemoryBarrierKind::ReadWrite;
    }
    if (HasReads) {
      return MemoryBarrierKind::Read;
    }
    if (HasWrites) {
      return MemoryBarrierKind::Write;
    }
    return MemoryBarrierKind::None;
  }

  MemoryBarrierKind getBarrierKind(uint32_t OpId) const {
    const MemoryOp *Op = findOp(OpId);
    return Op ? getBarrierKind(*Op) : MemoryBarrierKind::Unknown;
  }

  bool isBarrier(const MemoryOp &Op) const {
    return getBarrierKind(Op) != MemoryBarrierKind::None;
  }

private:
  const MemoryOp *findOp(uint32_t OpId) const {
    for (const MemoryOp &Op : Facts.Ops) {
      if (Op.Id == OpId) {
        return &Op;
      }
    }
    return nullptr;
  }

  const MemoryFacts &Facts;
};

// Inference: NoAlias/MayAlias query API over MemoryIntervals and MemoryOps.
class AliasAnalysis {
public:
  explicit AliasAnalysis(const MemoryFacts &Facts) : Facts(Facts) {}

  MemoryAliasResult alias(const MemoryInterval &LHS,
                          const MemoryInterval &RHS) const {
    return IntervalRelation::isKnownDisjoint(LHS, RHS)
               ? MemoryAliasResult::NoAlias
               : MemoryAliasResult::MayAlias;
  }

  MemoryAliasResult alias(const MemoryOp &LHS, const MemoryOp &RHS) const {
    for (const MemoryInterval &LHSInterval : LHS.Reads) {
      if (mayAliasAny(LHSInterval, RHS)) {
        return MemoryAliasResult::MayAlias;
      }
    }
    for (const MemoryInterval &LHSInterval : LHS.Writes) {
      if (mayAliasAny(LHSInterval, RHS)) {
        return MemoryAliasResult::MayAlias;
      }
    }
    return MemoryAliasResult::NoAlias;
  }

private:
  bool mayAliasAny(const MemoryInterval &Interval, const MemoryOp &Op) const {
    for (const MemoryInterval &Other : Op.Reads) {
      if (alias(Interval, Other) == MemoryAliasResult::MayAlias) {
        return true;
      }
    }
    for (const MemoryInterval &Other : Op.Writes) {
      if (alias(Interval, Other) == MemoryAliasResult::MayAlias) {
        return true;
      }
    }
    return false;
  }

  const MemoryFacts &Facts;
};

// Inference facade: the only public entry point intended for consumers. It
// keeps analysis internals private and exposes query APIs over MemoryFacts.
class MemoryAnalysisView {
public:
  explicit MemoryAnalysisView(const MemoryFacts &Facts)
      : Facts(Facts), Barriers(Facts), Aliases(Facts) {}

  const MemoryFacts &getFacts() const { return Facts; }

  const MemoryOp *getOp(uint32_t OpId) const {
    for (const MemoryOp &Op : Facts.Ops) {
      if (Op.Id == OpId) {
        return &Op;
      }
    }
    return nullptr;
  }

  MemoryBarrierKind getBarrierKind(const MemoryOp &Op) const {
    return Barriers.getBarrierKind(Op);
  }

  MemoryBarrierKind getBarrierKind(uint32_t OpId) const {
    return Barriers.getBarrierKind(OpId);
  }

  bool isBarrier(const MemoryOp &Op) const { return Barriers.isBarrier(Op); }

  IntervalRelationKind getIntervalRelation(const MemoryInterval &LHS,
                                           const MemoryInterval &RHS) const {
    return IntervalRelation::compare(LHS, RHS);
  }

  MemoryAliasResult alias(const MemoryInterval &LHS,
                          const MemoryInterval &RHS) const {
    return Aliases.alias(LHS, RHS);
  }

  MemoryAliasResult alias(const MemoryOp &LHS, const MemoryOp &RHS) const {
    return Aliases.alias(LHS, RHS);
  }

private:
  const MemoryFacts &Facts;
  BarrierAnalysis Barriers;
  AliasAnalysis Aliases;
};

} // namespace COMPILER

#endif // COMPILER_EVM_FRONTEND_EVM_MEMORY_ANALYSIS_H
