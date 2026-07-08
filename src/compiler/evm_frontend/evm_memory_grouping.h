// Copyright (C) 2026 the DTVM authors. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

#ifndef COMPILER_EVM_FRONTEND_EVM_MEMORY_GROUPING_H
#define COMPILER_EVM_FRONTEND_EVM_MEMORY_GROUPING_H

#include "compiler/evm_frontend/evm_memory_precheck.h"

#include <algorithm>
#include <cstdint>
#include <optional>

namespace COMPILER {

// Consumer result: a consecutive run of MemoryOps that can share one memory
// expansion precheck. It carries no store optimization decision.
struct ContiguousGroup {
  uint64_t EntryPC = 0;
  uint64_t FirstOpPC = 0;
  uint64_t LastOpPC = 0;
  uint64_t OpCount = 0;
  MemoryInterval UnionInterval;
};

// Consumer result: proof that the entire group interval can be prechecked once.
struct SharedPrecheck {
  ContiguousGroup Group;
  ProvenMemoryRange Range;
};

// Consumer: groups adjacent proven MemoryOps for shared memory precheck only.
// It consumes MemoryAnalysisView and MemoryPrecheckConsumer query APIs.
class MemoryGroupingConsumer final : public MemoryOptimizationPlanProvider {
public:
  MemoryGroupingConsumer(const MemoryAnalysisView &View,
                         const MemoryPrecheckConsumer &Prechecks)
      : View(View), Prechecks(Prechecks) {}

  std::optional<MemoryExpansionPlan>
  buildMemoryExpansionPlan(uint64_t EntryPC,
                           uint64_t BodyEndPC) const override {
    std::optional<SharedPrecheck> Shared =
        getSharedPrecheck(EntryPC, BodyEndPC);
    if (!Shared) {
      return std::nullopt;
    }
    return MemoryExpansionPlan::fromProvenRange(
        Shared->Range, MemoryExpansionKind::ContiguousGroup);
  }

  std::optional<SharedPrecheck> getSharedPrecheck(uint64_t EntryPC,
                                                  uint64_t BodyEndPC) const {
    std::optional<ContiguousGroup> Best;
    std::optional<ContiguousGroup> Current;
    std::optional<ProvenMemoryRange> PreviousProof;

    for (const MemoryOp &Op : View.getFacts().Ops) {
      if (Op.Pc < EntryPC) {
        continue;
      }
      if (Op.Pc >= BodyEndPC) {
        break;
      }

      std::optional<ProvenMemoryRange> Proof =
          Prechecks.getOpPrecheckRange(EntryPC, Op);
      if (!Proof) {
        const MemoryBarrierKind Barrier = View.getBarrierKind(Op);
        finishGroup(Current, Best);
        PreviousProof.reset();
        if (Barrier != MemoryBarrierKind::None) {
          continue;
        }
        continue;
      }

      if (!canAppend(Current, PreviousProof, *Proof)) {
        finishGroup(Current, Best);
        Current.reset();
        PreviousProof.reset();
      }

      if (!Current) {
        Current = makeGroup(EntryPC, *Proof);
      } else if (!append(*Current, *Proof)) {
        finishGroup(Current, Best);
        Current = makeGroup(EntryPC, *Proof);
      }

      PreviousProof = Proof;
    }

    finishGroup(Current, Best);
    if (!Best || Best->OpCount < 2) {
      return std::nullopt;
    }

    SharedPrecheck Result;
    Result.Group = *Best;
    Result.Range.EntryPC = Best->EntryPC;
    Result.Range.FirstOpPC = Best->FirstOpPC;
    Result.Range.LastOpPC = Best->LastOpPC;
    Result.Range.CoveredOpCount = Best->OpCount;
    Result.Range.Interval = Best->UnionInterval;
    return Result;
  }

private:
  static bool getBounds(const MemoryInterval &Interval, uint64_t &Begin,
                        uint64_t &End) {
    if (Interval.Space != AddressSpace::Memory || !Interval.Addr.isKnown() ||
        Interval.Addr.Kind != AddressBaseKind::Const || !Interval.Size.Known ||
        Interval.Addr.Offset < 0) {
      return false;
    }
    Begin = static_cast<uint64_t>(Interval.Addr.Offset);
    if (Interval.Size.Value > UINT64_MAX - Begin) {
      return false;
    }
    End = Begin + Interval.Size.Value;
    return true;
  }

  bool canAppend(const std::optional<ContiguousGroup> &Current,
                 const std::optional<ProvenMemoryRange> &PreviousProof,
                 const ProvenMemoryRange &NextProof) const {
    if (!Current || !PreviousProof) {
      return true;
    }
    if (View.alias(PreviousProof->Interval, NextProof.Interval) !=
        MemoryAliasResult::NoAlias) {
      return false;
    }

    uint64_t PrevBegin = 0;
    uint64_t PrevEnd = 0;
    uint64_t NextBegin = 0;
    uint64_t NextEnd = 0;
    if (!getBounds(PreviousProof->Interval, PrevBegin, PrevEnd) ||
        !getBounds(NextProof.Interval, NextBegin, NextEnd)) {
      return false;
    }
    (void)PrevBegin;
    (void)NextEnd;
    return PrevEnd == NextBegin;
  }

  static ContiguousGroup makeGroup(uint64_t EntryPC,
                                   const ProvenMemoryRange &Proof) {
    ContiguousGroup Group;
    Group.EntryPC = EntryPC;
    Group.FirstOpPC = Proof.FirstOpPC;
    Group.LastOpPC = Proof.LastOpPC;
    Group.OpCount = 1;
    Group.UnionInterval = Proof.Interval;
    return Group;
  }

  static bool append(ContiguousGroup &Group, const ProvenMemoryRange &Proof) {
    uint64_t GroupBegin = 0;
    uint64_t GroupEnd = 0;
    uint64_t ProofBegin = 0;
    uint64_t ProofEnd = 0;
    if (!getBounds(Group.UnionInterval, GroupBegin, GroupEnd) ||
        !getBounds(Proof.Interval, ProofBegin, ProofEnd)) {
      return false;
    }

    const uint64_t UnionBegin = std::min(GroupBegin, ProofBegin);
    const uint64_t UnionEnd = std::max(GroupEnd, ProofEnd);
    Group.LastOpPC = Proof.LastOpPC;
    ++Group.OpCount;
    Group.UnionInterval.Space = AddressSpace::Memory;
    Group.UnionInterval.Addr = AddressExpr::constant(UnionBegin);
    Group.UnionInterval.Size = SizeExpr::constant(UnionEnd - UnionBegin);
    Group.UnionInterval.Empty = UnionBegin == UnionEnd;
    return true;
  }

  static void finishGroup(std::optional<ContiguousGroup> &Current,
                          std::optional<ContiguousGroup> &Best) {
    if (Current && Current->OpCount >= 2 &&
        (!Best || Current->OpCount > Best->OpCount)) {
      Best = Current;
    }
    Current.reset();
  }

  const MemoryAnalysisView &View;
  const MemoryPrecheckConsumer &Prechecks;
};

// Facade used by lowering: tries consumer providers in priority order and
// returns only a MemoryExpansionPlan.
class MemoryExpansionPlanner final : public MemoryOptimizationPlanProvider {
public:
  explicit MemoryExpansionPlanner(const MemoryAnalysisView &View)
      : Prechecks(View), Grouping(View, Prechecks) {}

  std::optional<MemoryExpansionPlan>
  buildMemoryExpansionPlan(uint64_t EntryPC,
                           uint64_t BodyEndPC) const override {
    LastDiagnostics.clear();

    if (std::optional<SharedPrecheck> Shared =
            Grouping.getSharedPrecheck(EntryPC, BodyEndPC)) {
      ++LastDiagnostics.GroupingCandidates;
      MemoryExpansionPlanRejectReason Reason =
          MemoryExpansionPlanRejectReason::None;
      if (std::optional<MemoryExpansionPlan> GroupPlan =
              MemoryExpansionPlan::fromProvenRange(
                  Shared->Range, MemoryExpansionKind::ContiguousGroup, true,
                  &Reason)) {
        ++LastDiagnostics.GroupingAccepted;
        return GroupPlan;
      }
      LastDiagnostics.noteReject(Reason);
    } else {
      LastDiagnostics.noteReject(MemoryExpansionPlanRejectReason::NoCandidate);
    }

    if (std::optional<ProvenMemoryRange> Range =
            Prechecks.getBlockPrecheckRange(EntryPC, BodyEndPC)) {
      ++LastDiagnostics.PrecheckCandidates;
      MemoryExpansionPlanRejectReason Reason =
          MemoryExpansionPlanRejectReason::None;
      if (std::optional<MemoryExpansionPlan> PrecheckPlan =
              MemoryExpansionPlan::fromProvenRange(
                  *Range, MemoryExpansionKind::ProvenRange, true, &Reason)) {
        ++LastDiagnostics.PrecheckAccepted;
        return PrecheckPlan;
      }
      LastDiagnostics.noteReject(Reason);
    } else {
      LastDiagnostics.noteReject(MemoryExpansionPlanRejectReason::NoCandidate);
    }

    return std::nullopt;
  }

  const MemoryExpansionPlanDiagnostics &getLastDiagnostics() const {
    return LastDiagnostics;
  }

private:
  MemoryPrecheckConsumer Prechecks;
  MemoryGroupingConsumer Grouping;
  mutable MemoryExpansionPlanDiagnostics LastDiagnostics;
};

} // namespace COMPILER

#endif // COMPILER_EVM_FRONTEND_EVM_MEMORY_GROUPING_H
