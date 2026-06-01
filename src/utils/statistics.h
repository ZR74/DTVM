// Copyright (C) 2021-2023 the DTVM authors. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

#ifndef ZEN_UTILS_STATISTICS_H
#define ZEN_UTILS_STATISTICS_H

#include "common/defines.h"

#include <chrono>
#include <unordered_map>
#include <vector>

namespace zen::utils {

enum class StatisticPhase : uint32_t {
  Load = 0,
  RuntimeSetup = 1,          // mainly for EVM CLI cold-start staging
  StateFileRead = 2,         // mainly for EVM CLI replay state file IO
  StateJsonParse = 3,        // mainly for EVM CLI replay JSON parse
  StateMaterialization = 4,  // mainly for EVM CLI account/storage import
  StateAccessListWarmup = 5, // mainly for EVM CLI access-list warmup
  InputDecode = 6,           // mainly for EVM CLI calldata/input decode
  MessageSetup = 7,          // mainly for EVM CLI message preparation
  PreExecutionChecks = 8,    // mainly for EVM CLI pre-execution checks
  JITCompilation = 9,        // only for JIT mode
  JITLazyPrecompilation = 10,// only for multipass JIT lazy mode
  JITLazyFgCompilation = 11, // only for multipass JIT lazy mode(foreground)
  JITLazyBgCompilation = 12, // only for multipass JIT lazy mode(background)
  JITLazyReleaseDelay = 13,  // only for multipass JIT lazy mode
  MemoryBucketMap = 14,
  Instantiation = 15,
  Execution = 16,
  PostExecutionCleanup = 17, // mainly for EVM CLI output/save/unload stages
  NumStatisticPhases
};

class Statistics final {
  typedef common::SteadyClock::time_point TimePoint;
  typedef uint32_t StatisticTimer;
  typedef std::pair<StatisticPhase, float> StatisticRecord;

public:
  Statistics(bool Enabled) : Enabled(Enabled) {}

  ~Statistics() { ZEN_ASSERT(Timers.empty()); }

  NONCOPYABLE(Statistics);

  StatisticTimer startRecord(StatisticPhase Phase);

  void stopRecord(StatisticTimer Timer);

  void revertRecord(StatisticTimer Timer);

  void clearAllTimers();

  void report() const;

private:
  const bool Enabled;
  common::Mutex Mtx;
  StatisticTimer TimerCounter = 0;
  typedef std::pair<StatisticPhase, TimePoint> TimerPair;
  std::unordered_map<StatisticTimer, TimerPair> Timers;
  std::vector<StatisticRecord> Records;
};

} // namespace zen::utils

#endif // ZEN_UTILS_STATISTICS_H
