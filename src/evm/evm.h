// Copyright (C) 2025 the DTVM authors. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

#include "evmc/evmc.hpp"

namespace zen {
namespace evm {
// Limit required memory size to prevent excessive memory consumption
constexpr uint64_t MAX_REQUIRED_MEMORY_SIZE = 1024 * 1024;

constexpr evmc_revision DEFAULT_REVISION = EVMC_CANCUN;

// About gas cost
constexpr auto COLD_ACCOUNT_ACCESS_COST = 2600;
constexpr auto WARM_ACCOUNT_ACCESS_COST = 100;
constexpr auto ADDITIONAL_COLD_ACCOUNT_ACCESS_COST =
    COLD_ACCOUNT_ACCESS_COST - WARM_ACCOUNT_ACCESS_COST;
constexpr auto COLD_SLOAD_COST = 2100;
constexpr auto WARM_STORAGE_READ_COST = 100;
constexpr auto CALL_VALUE_COST = 9000;
constexpr auto ACCOUNT_CREATION_COST = 25000;
constexpr auto CALL_GAS_STIPEND = 2300;

constexpr auto MAX_SIZE_OF_INITCODE = 0xC000;

/// The gas cost specification for storage instructions.
struct StorageCostSpec {
  bool NetCost;       ///< Is this net gas cost metering schedule?
  int16_t WarmAccess; ///< Storage warm access cost, YP: G_{warmaccess}
  int16_t Set;        ///< Storage addition cost, YP: G_{sSet}
  int16_t ReSet;      ///< Storage modification cost, YP: G_{sReSet}
  int16_t Clear;      ///< Storage deletion refund, YP: R_{sClear}
};

/// Table of gas cost specification for storage instructions per EVM revision.
/// TODO: This can be moved to instruction traits and be used in other places:
/// e.g.
///       SLOAD cost, replacement for warm_storage_read_cost.
constexpr auto storage_cost_spec = []() noexcept {
  std::array<StorageCostSpec, EVMC_MAX_REVISION + 1> tbl{};

  // Legacy cost schedule.
  for (auto rev : {EVMC_FRONTIER, EVMC_HOMESTEAD, EVMC_TANGERINE_WHISTLE,
                   EVMC_SPURIOUS_DRAGON, EVMC_BYZANTIUM, EVMC_PETERSBURG})
    tbl[rev] = {false, 200, 20000, 5000, 15000};

  // Net cost schedule.
  tbl[EVMC_CONSTANTINOPLE] = {true, 200, 20000, 5000, 15000};
  tbl[EVMC_ISTANBUL] = {true, 800, 20000, 5000, 15000};
  tbl[EVMC_BERLIN] = {true, WARM_STORAGE_READ_COST, 20000,
                      5000 - COLD_SLOAD_COST, 15000};
  tbl[EVMC_LONDON] = {true, WARM_STORAGE_READ_COST, 20000,
                      5000 - COLD_SLOAD_COST, 4800};
  tbl[EVMC_PARIS] = tbl[EVMC_LONDON];
  tbl[EVMC_SHANGHAI] = tbl[EVMC_LONDON];
  tbl[EVMC_CANCUN] = tbl[EVMC_LONDON];
  tbl[EVMC_PRAGUE] = tbl[EVMC_LONDON];
  tbl[EVMC_OSAKA] = tbl[EVMC_LONDON];
  tbl[EVMC_EXPERIMENTAL] = tbl[EVMC_LONDON];
  return tbl;
}();

struct StorageStoreCost {
  int16_t gas_cost;
  int16_t gas_refund;
};

// The lookup table of SSTORE costs by the storage update status.
constexpr auto sstore_costs = []() noexcept {
  std::array<std::array<StorageStoreCost, EVMC_STORAGE_MODIFIED_RESTORED + 1>,
             EVMC_MAX_REVISION + 1>
      tbl{};

  for (size_t rev = EVMC_FRONTIER; rev <= EVMC_MAX_REVISION; ++rev) {
    auto &e = tbl[rev];
    if (const auto c = storage_cost_spec[rev]; !c.NetCost) // legacy
    {
      e[EVMC_STORAGE_ADDED] = {c.Set, 0};
      e[EVMC_STORAGE_DELETED] = {c.ReSet, c.Clear};
      e[EVMC_STORAGE_MODIFIED] = {c.ReSet, 0};
      e[EVMC_STORAGE_ASSIGNED] = e[EVMC_STORAGE_MODIFIED];
      e[EVMC_STORAGE_DELETED_ADDED] = e[EVMC_STORAGE_ADDED];
      e[EVMC_STORAGE_MODIFIED_DELETED] = e[EVMC_STORAGE_DELETED];
      e[EVMC_STORAGE_DELETED_RESTORED] = e[EVMC_STORAGE_ADDED];
      e[EVMC_STORAGE_ADDED_DELETED] = e[EVMC_STORAGE_DELETED];
      e[EVMC_STORAGE_MODIFIED_RESTORED] = e[EVMC_STORAGE_MODIFIED];
    } else // net cost
    {
      e[EVMC_STORAGE_ASSIGNED] = {c.WarmAccess, 0};
      e[EVMC_STORAGE_ADDED] = {c.Set, 0};
      e[EVMC_STORAGE_DELETED] = {c.ReSet, c.Clear};
      e[EVMC_STORAGE_MODIFIED] = {c.ReSet, 0};
      e[EVMC_STORAGE_DELETED_ADDED] = {c.WarmAccess,
                                       static_cast<int16_t>(-c.Clear)};
      e[EVMC_STORAGE_MODIFIED_DELETED] = {c.WarmAccess, c.Clear};
      e[EVMC_STORAGE_DELETED_RESTORED] = {
          c.WarmAccess, static_cast<int16_t>(c.ReSet - c.WarmAccess - c.Clear)};
      e[EVMC_STORAGE_ADDED_DELETED] = {
          c.WarmAccess, static_cast<int16_t>(c.Set - c.WarmAccess)};
      e[EVMC_STORAGE_MODIFIED_RESTORED] = {
          c.WarmAccess, static_cast<int16_t>(c.ReSet - c.WarmAccess)};
    }
  }

  return tbl;
}();
} // namespace evm
} // namespace zen
