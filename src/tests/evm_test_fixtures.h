// Copyright (C) 2025 the DTVM authors. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

#ifndef ZEN_TESTS_EVM_TEST_FIXTURES_H
#define ZEN_TESTS_EVM_TEST_FIXTURES_H

#include "evmc/mocked_host.hpp"

#include <memory>
#include <rapidjson/document.h>
#include <string>
#include <vector>

namespace zen {
namespace test_utils {

// Represents a parsed account from test fixture data
struct ParsedAccount {
  evmc::address Address;
  evmc::MockedAccount Account;
};

// Represents a parsed transaction from test fixture data
// This structure bridges the gap between raw JSON test data and EVMC execution
// format
//
// Creation flow:
// 1. StateTestFixture contains raw JSON transaction arrays (gas[], value[],
// data[])
// 2. ForkPostResult provides indexes to select specific array elements
// 3. createTransactionFromIndex() combines these to create ParsedTransaction
// 4. ParsedTransaction provides EVMC-ready execution parameters
//
// The unique_ptr<evmc_message> allows for:
// - Dynamic allocation of variable-sized message data
// - Proper lifetime management during test execution
// - Easy conversion to EVMC function call parameters
struct ParsedTransaction {
  evmc_tx_context TxContext;
  std::unique_ptr<evmc_message> Message;
  std::vector<uint8_t> CallData;
};

// Main test fixture data structure containing all test case information
// This class manages ownership of JSON documents and provides move semantics
// for efficient handling of large test data structures
//
// Relationship hierarchy:
// StateTestFixture (top-level test container)
//   ├── PreState (vector of ParsedAccount) - initial blockchain state
//   ├── Environment (evmc_tx_context) - block environment parameters
//   ├── Transaction (JSON document) - raw transaction data with arrays
//   └── Post (JSON document) - expected results per fork
//
// The copy constructor and assignment are deleted because:
// 1. JSON documents are expensive to deep-copy
// 2. Prevents accidental copying of large test data
// 3. Enforces intentional move semantics for performance
struct StateTestFixture {
  std::string TestName;
  std::vector<ParsedAccount> PreState;
  evmc_tx_context Environment;
  std::unique_ptr<rapidjson::Document> Transaction;
  std::unique_ptr<rapidjson::Document> Post;

  // Move-only semantics to avoid expensive copying of JSON documents
  StateTestFixture() = default;
  StateTestFixture(const StateTestFixture &) = delete;
  StateTestFixture &operator=(const StateTestFixture &) = delete;
  StateTestFixture(StateTestFixture &&) = default;
  StateTestFixture &operator=(StateTestFixture &&) = default;
};

// Contains expected results and indexes for a specific fork configuration
struct ForkPostResult {
  std::string ExpectedHash;
  std::string ExpectedLogs;
  std::string ExpectedException;
  std::vector<uint8_t> ExpectedTxBytes;
  struct {
    size_t Data = 0;
    size_t Gas = 0;
    size_t Value = 0;
  } Indexes;
};

// Parsing functions for test fixture data
evmc::address parseAddress(const std::string &HexAddr);
evmc::bytes32 parseBytes32(const std::string &HexStr);
evmc::uint256be parseUint256(const std::string &HexStr);
std::vector<uint8_t> parseHexData(const std::string &HexStr);

std::vector<ParsedAccount> parsePreAccounts(const rapidjson::Value &Pre);
void addAccountToMockedHost(evmc::MockedHost &Host, const evmc::address &Addr,
                            const evmc::MockedAccount &Account);

// State test file discovery and parsing
std::vector<std::string> findJsonFiles(const std::string &RootPath);
std::vector<StateTestFixture> parseStateTestFile(const std::string &FilePath);

// Fork-specific result parsing and transaction creation
ForkPostResult parseForkPostResult(const rapidjson::Value &PostResult);
ParsedTransaction
createTransactionFromIndex(const rapidjson::Document &Transaction,
                           const ForkPostResult &Result);

} // namespace test_utils
} // namespace zen

#endif // ZEN_TESTS_EVM_TEST_FIXTURES_H
