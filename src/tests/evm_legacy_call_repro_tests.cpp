// Copyright (C) 2026 the DTVM authors. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

#include <filesystem>
#include <fstream>
#include <optional>
#include <string>
#include <unordered_map>
#include <vector>

#include <gtest/gtest.h>
#include <rapidjson/document.h>
#include <rapidjson/istreamwrapper.h>

#include "evm/evm.h"
#include "evm_test_host.hpp"
#include "runtime/runtime.h"
#include "utils/evm.h"
#ifdef ZEN_ENABLE_LIBEVM
#include "vm/dt_evmc_vm.h"
#endif
#include <evmc/evmc.hpp>

using namespace zen;
using namespace zen::evm;
using namespace zen::runtime;

namespace {

struct ParsedFixture {
  bool IsValid = false;
  std::string CaseName;
  std::string FixturePath;
  evmc_revision Revision = EVMC_FRONTIER;
  evmc_tx_context TxContext{};
  evmc_message Message{};
  uint64_t GasLimit = 0;
  uint64_t IntrinsicGas = 0;
  evmc::bytes Input;
  evmc::bytes Bytecode;
  std::vector<ZenMockedEVMHost::AccountInitEntry> Accounts;
  std::string ExpectedStatus;
  uint64_t ExpectedTxGas = 0;
  uint64_t ExpectedDTVMInterpGas = 0;
  uint64_t ExpectedDTVMMultipassGas = 0;
  std::optional<evmc::bytes32> BlockHash;
  std::unordered_map<int64_t, evmc::bytes32> BlockHashes;
};

class FixtureHost : public ZenMockedEVMHost {
public:
  std::unordered_map<int64_t, evmc::bytes32> BlockHashOverrides;

  evmc::bytes32 get_block_hash(int64_t BlockNumber) const noexcept override {
    auto It = BlockHashOverrides.find(BlockNumber);
    if (It != BlockHashOverrides.end()) {
      return It->second;
    }
    return ZenMockedEVMHost::get_block_hash(BlockNumber);
  }
};

evmc_revision parseRevision(const std::string &Revision) {
  if (Revision == "EVMC_FRONTIER")
    return EVMC_FRONTIER;
  if (Revision == "EVMC_TANGERINE_WHISTLE")
    return EVMC_TANGERINE_WHISTLE;
  if (Revision == "EVMC_SPURIOUS_DRAGON")
    return EVMC_SPURIOUS_DRAGON;
  if (Revision == "EVMC_BYZANTIUM")
    return EVMC_BYZANTIUM;
  if (Revision == "EVMC_CONSTANTINOPLE")
    return EVMC_CONSTANTINOPLE;
  if (Revision == "EVMC_PETERSBURG")
    return EVMC_PETERSBURG;
  if (Revision == "EVMC_ISTANBUL")
    return EVMC_ISTANBUL;
  if (Revision == "EVMC_BERLIN")
    return EVMC_BERLIN;
  if (Revision == "EVMC_LONDON")
    return EVMC_LONDON;
  if (Revision == "EVMC_PARIS")
    return EVMC_PARIS;
  if (Revision == "EVMC_SHANGHAI")
    return EVMC_SHANGHAI;
  if (Revision == "EVMC_CANCUN")
    return EVMC_CANCUN;
  return EVMC_FRONTIER;
}

std::filesystem::path getLegacyReproFixtureDir() {
  return std::filesystem::path(__FILE__).parent_path() /
         std::filesystem::path("../../tests/evm/fixtures/legacy_call_repro");
}

ParsedFixture loadFixture(const std::filesystem::path &Path) {
  auto failFixture = [&](const std::string &Message) {
    ADD_FAILURE() << Message << ": " << Path.string();
    ParsedFixture Fixture;
    Fixture.FixturePath = Path.string();
    return Fixture;
  };
  auto requireObjectMember = [&](const rapidjson::Value &Object,
                                 const char *Name) -> bool {
    return Object.HasMember(Name) && Object[Name].IsObject();
  };
  auto requireStringMember = [&](const rapidjson::Value &Object,
                                 const char *Name) -> bool {
    return Object.HasMember(Name) && Object[Name].IsString();
  };
  auto requireUint64Member = [&](const rapidjson::Value &Object,
                                 const char *Name) -> bool {
    return Object.HasMember(Name) && Object[Name].IsUint64();
  };

  std::ifstream File(Path);
  if (!File.is_open()) {
    return failFixture("failed to open fixture");
  }

  rapidjson::IStreamWrapper ISW(File);
  rapidjson::Document Doc;
  Doc.ParseStream(ISW);
  if (Doc.HasParseError()) {
    return failFixture("parse error in fixture");
  }
  if (!Doc.IsObject()) {
    return failFixture("fixture root must be object");
  }
  if (!requireStringMember(Doc, "case_name")) {
    return failFixture("fixture.case_name must be a string");
  }
  if (!requireStringMember(Doc, "revision")) {
    return failFixture("fixture.revision must be a string");
  }
  if (!requireObjectMember(Doc, "tx")) {
    return failFixture("fixture.tx must be an object");
  }
  if (!requireObjectMember(Doc, "env")) {
    return failFixture("fixture.env must be an object");
  }
  if (!requireObjectMember(Doc, "prestate")) {
    return failFixture("fixture.prestate must be an object");
  }
  if (!requireObjectMember(Doc, "expected")) {
    return failFixture("fixture.expected must be an object");
  }

  ParsedFixture Fixture;
  Fixture.FixturePath = Path.string();
  Fixture.CaseName = Doc["case_name"].GetString();
  Fixture.Revision = parseRevision(Doc["revision"].GetString());

  const auto &Tx = Doc["tx"];
  const auto &Env = Doc["env"];
  const auto &Prestate = Doc["prestate"];
  const auto &Expected = Doc["expected"];

  if (!requireStringMember(Tx, "from")) {
    return failFixture("fixture.tx.from must be a string");
  }
  if (!requireStringMember(Tx, "to")) {
    return failFixture("fixture.tx.to must be a string");
  }
  if (!requireStringMember(Tx, "input")) {
    return failFixture("fixture.tx.input must be a string");
  }
  if (!requireUint64Member(Tx, "gas_limit")) {
    return failFixture("fixture.tx.gas_limit must be a uint64");
  }
  if (!requireStringMember(Tx, "gas_price")) {
    return failFixture("fixture.tx.gas_price must be a string");
  }
  if (!requireStringMember(Tx, "value")) {
    return failFixture("fixture.tx.value must be a string");
  }
  if (!requireUint64Member(Env, "block_number")) {
    return failFixture("fixture.env.block_number must be a uint64");
  }
  if (!requireUint64Member(Env, "block_timestamp")) {
    return failFixture("fixture.env.block_timestamp must be a uint64");
  }
  if (!requireStringMember(Env, "block_coinbase")) {
    return failFixture("fixture.env.block_coinbase must be a string");
  }
  if (!requireStringMember(Env, "block_prev_randao")) {
    return failFixture("fixture.env.block_prev_randao must be a string");
  }
  if (!requireUint64Member(Env, "block_gas_limit")) {
    return failFixture("fixture.env.block_gas_limit must be a uint64");
  }
  if (!requireStringMember(Env, "block_base_fee")) {
    return failFixture("fixture.env.block_base_fee must be a string");
  }
  if (!requireStringMember(Env, "tx_origin")) {
    return failFixture("fixture.env.tx_origin must be a string");
  }
  if (!requireStringMember(Expected, "status")) {
    return failFixture("fixture.expected.status must be a string");
  }
  if (!requireUint64Member(Expected, "tx_gas")) {
    return failFixture("fixture.expected.tx_gas must be a uint64");
  }
  if (Expected.HasMember("dtvm_interpreter_gas") &&
      !Expected["dtvm_interpreter_gas"].IsUint64()) {
    return failFixture(
        "fixture.expected.dtvm_interpreter_gas must be a uint64");
  }
  if (Expected.HasMember("dtvm_multipass_gas") &&
      !Expected["dtvm_multipass_gas"].IsUint64()) {
    return failFixture("fixture.expected.dtvm_multipass_gas must be a uint64");
  }

  const std::string From = Tx["from"].GetString();
  const std::string To = Tx["to"].GetString();
  const std::string InputHex = Tx["input"].GetString();

  Fixture.GasLimit = Tx["gas_limit"].GetUint64();
  Fixture.Input = zen::utils::hexToBytes(InputHex);

  Fixture.TxContext.tx_gas_price =
      zen::utils::parseUint256(Tx["gas_price"].GetString());
  Fixture.TxContext.block_number = Env["block_number"].GetUint64();
  Fixture.TxContext.block_timestamp = Env["block_timestamp"].GetUint64();
  Fixture.TxContext.block_coinbase =
      zen::utils::parseAddress(Env["block_coinbase"].GetString());
  Fixture.TxContext.block_prev_randao =
      zen::utils::parseUint256(Env["block_prev_randao"].GetString());
  Fixture.TxContext.block_gas_limit = Env["block_gas_limit"].GetUint64();
  Fixture.TxContext.block_base_fee =
      zen::utils::parseUint256(Env["block_base_fee"].GetString());
  Fixture.TxContext.tx_origin =
      zen::utils::parseAddress(Env["tx_origin"].GetString());
  if (Env.HasMember("block_hash") && Env["block_hash"].IsString()) {
    Fixture.BlockHash = zen::utils::parseBytes32(Env["block_hash"].GetString());
  }
  if (Env.HasMember("block_hashes") && Env["block_hashes"].IsObject()) {
    for (auto It = Env["block_hashes"].MemberBegin();
         It != Env["block_hashes"].MemberEnd(); ++It) {
      if (!It->value.IsString()) {
        return failFixture("fixture.env.block_hashes values must be strings");
      }
      int64_t BlockNum = std::stoll(It->name.GetString());
      Fixture.BlockHashes[BlockNum] =
          zen::utils::parseBytes32(It->value.GetString());
    }
  }

  Fixture.Message = {};
  Fixture.Message.kind = EVMC_CALL;
  Fixture.Message.flags = 0u;
  Fixture.Message.depth = 0;
  Fixture.Message.gas = static_cast<int64_t>(Fixture.GasLimit);
  Fixture.Message.recipient = zen::utils::parseAddress(To);
  Fixture.Message.sender = zen::utils::parseAddress(From);
  Fixture.Message.value = zen::utils::parseUint256(Tx["value"].GetString());
  Fixture.Message.code = nullptr;
  Fixture.Message.code_size = 0;
  Fixture.Message.input_data =
      Fixture.Input.empty() ? nullptr : Fixture.Input.data();
  Fixture.Message.input_size = Fixture.Input.size();

  for (auto It = Prestate.MemberBegin(); It != Prestate.MemberEnd(); ++It) {
    const std::string AddressStr = It->name.GetString();
    const auto &AccountVal = It->value;
    if (!AccountVal.IsObject()) {
      return failFixture("fixture.prestate entries must be objects");
    }
    if (!requireStringMember(AccountVal, "balance")) {
      return failFixture("fixture.prestate[*].balance must be a string");
    }
    if (!requireUint64Member(AccountVal, "nonce")) {
      return failFixture("fixture.prestate[*].nonce must be a uint64");
    }
    if (!requireStringMember(AccountVal, "code")) {
      return failFixture("fixture.prestate[*].code must be a string");
    }
    if (!requireObjectMember(AccountVal, "storage")) {
      return failFixture("fixture.prestate[*].storage must be an object");
    }

    ZenMockedEVMHost::AccountInitEntry Entry;
    Entry.Address = zen::utils::parseAddress(AddressStr);
    Entry.Account.balance =
        zen::utils::parseUint256(AccountVal["balance"].GetString());
    Entry.Account.nonce = AccountVal["nonce"].GetUint64();
    Entry.Account.code = zen::utils::hexToBytes(AccountVal["code"].GetString());

    const auto &Storage = AccountVal["storage"];
    for (auto Sit = Storage.MemberBegin(); Sit != Storage.MemberEnd(); ++Sit) {
      if (!Sit->value.IsString()) {
        return failFixture(
            "fixture.prestate[*].storage values must be strings");
      }
      evmc::StorageValue SV{};
      SV.current = zen::utils::parseBytes32(Sit->value.GetString());
      Entry.Account.storage[zen::utils::parseBytes32(Sit->name.GetString())] =
          SV;
    }

    if (AddressStr == To) {
      Fixture.Bytecode = Entry.Account.code;
    }

    Fixture.Accounts.push_back(std::move(Entry));
  }

  Fixture.ExpectedStatus = Expected["status"].GetString();
  Fixture.ExpectedTxGas = Expected["tx_gas"].GetUint64();
  Fixture.ExpectedDTVMInterpGas =
      Expected.HasMember("dtvm_interpreter_gas")
          ? Expected["dtvm_interpreter_gas"].GetUint64()
          : Fixture.ExpectedTxGas;
  Fixture.ExpectedDTVMMultipassGas =
      Expected.HasMember("dtvm_multipass_gas")
          ? Expected["dtvm_multipass_gas"].GetUint64()
          : Fixture.ExpectedTxGas;
  Fixture.IntrinsicGas = zen::utils::computeIntrinsicGas(
      Fixture.Revision, EVMC_CALL, Fixture.Message.input_data,
      Fixture.Message.input_size);
  Fixture.IsValid = true;

  return Fixture;
}

ZenMockedEVMHost::TransactionExecutionResult
runFixture(const ParsedFixture &Fixture, common::RunMode Mode) {
  RuntimeConfig Config;
  Config.Format = common::InputFormat::EVM;
  Config.Mode = Mode;
  Config.EnableEvmGasMetering = true;

  auto Host = std::make_unique<FixtureHost>();
  Host->loadInitialState(Fixture.TxContext, Fixture.Accounts, true);
  if (Fixture.BlockHash.has_value()) {
    // Most legacy contracts use BLOCKHASH(block.number-1); mocked host exposes
    // one block_hash value for all get_block_hash() queries.
    Host->block_hash = *Fixture.BlockHash;
  }
  Host->BlockHashOverrides = Fixture.BlockHashes;
  auto RT = Runtime::newEVMRuntime(Config, Host.get());
  EXPECT_TRUE(RT != nullptr);
  Host->setRuntime(RT.get());

  ZenMockedEVMHost::TransactionExecutionConfig ExecConfig;
  ExecConfig.ModuleName =
      Fixture.CaseName + "-" +
      (Mode == common::RunMode::InterpMode ? "interp" : "multipass");
  ExecConfig.Bytecode =
      reinterpret_cast<const uint8_t *>(Fixture.Bytecode.data());
  ExecConfig.BytecodeSize = Fixture.Bytecode.size();
  ExecConfig.Message = Fixture.Message;
  ExecConfig.GasLimit = Fixture.GasLimit;
  ExecConfig.IntrinsicGas = Fixture.IntrinsicGas;
  ExecConfig.Revision = Fixture.Revision;

  return Host->executeTransaction(ExecConfig);
}

struct VmExecutionResult {
  bool Success = false;
  evmc_status_code Status = EVMC_INTERNAL_ERROR;
  uint64_t GasCharged = 0;
};

#ifdef ZEN_ENABLE_LIBEVM
VmExecutionResult runFixtureViaDTVMApi(const ParsedFixture &Fixture,
                                       const char *ModeValue) {
  auto Host = std::make_unique<FixtureHost>();
  Host->loadInitialState(Fixture.TxContext, Fixture.Accounts, true);
  if (Fixture.BlockHash.has_value()) {
    Host->block_hash = *Fixture.BlockHash;
  }
  Host->BlockHashOverrides = Fixture.BlockHashes;
  RuntimeConfig HostConfig;
  HostConfig.Format = common::InputFormat::EVM;
  HostConfig.Mode = std::strcmp(ModeValue, "interpreter") == 0
                        ? common::RunMode::InterpMode
                        : common::RunMode::MultipassMode;
  HostConfig.EnableEvmGasMetering = true;
  auto HostRuntime = Runtime::newEVMRuntime(HostConfig, Host.get());
  EXPECT_TRUE(HostRuntime != nullptr);
  Host->setRuntime(HostRuntime.get());
  auto Vm = evmc_create_dtvmapi();
  EXPECT_NE(Vm, nullptr);
  if (!Vm) {
    return {};
  }
  if (Vm->set_option == nullptr) {
    ADD_FAILURE() << "dtvmapi VM does not provide set_option";
    Vm->destroy(Vm);
    return {};
  }
  const auto SetModeResult = Vm->set_option(Vm, "mode", ModeValue);
  if (SetModeResult != EVMC_SET_OPTION_SUCCESS) {
    ADD_FAILURE() << "failed to set dtvmapi mode to " << ModeValue
                  << ", result=" << SetModeResult;
    Vm->destroy(Vm);
    return {};
  }
  const auto SetGasMeteringResult =
      Vm->set_option(Vm, "enable_gas_metering", "true");
  if (SetGasMeteringResult != EVMC_SET_OPTION_SUCCESS) {
    ADD_FAILURE() << "failed to enable dtvmapi gas metering, result="
                  << SetGasMeteringResult;
    Vm->destroy(Vm);
    return {};
  }

  evmc_message Msg = Fixture.Message;
  Msg.gas = static_cast<int64_t>(Fixture.GasLimit);

  const auto To = Msg.recipient;
  const auto It = Host->accounts.find(To);
  if (It == Host->accounts.end()) {
    Vm->destroy(Vm);
    return {};
  }
  const auto &Code = It->second.code;
  evmc_result Raw =
      Vm->execute(Vm, &evmc::MockedHost::get_interface(),
                  reinterpret_cast<evmc_host_context *>(Host.get()),
                  Fixture.Revision, &Msg, Code.data(), Code.size());

  VmExecutionResult Result;
  Result.Success = true;
  Result.Status = Raw.status_code;
  if (Raw.gas_left >= 0) {
    Result.GasCharged = Fixture.GasLimit - static_cast<uint64_t>(Raw.gas_left);
  }
  if (Raw.release) {
    Raw.release(&Raw);
  }
  Vm->destroy(Vm);
  return Result;
}
#endif

void assertExpectedStatus(const std::string &ExpectedStatus,
                          const evmc_status_code ActualStatus) {
  if (ExpectedStatus == "success") {
    EXPECT_EQ(ActualStatus, EVMC_SUCCESS);
    return;
  }
  if (ExpectedStatus == "revert") {
    EXPECT_EQ(ActualStatus, EVMC_REVERT);
    return;
  }
  EXPECT_NE(ActualStatus, EVMC_SUCCESS);
}

} // namespace

TEST(EVMLegacyCallReproTest, ExecuteFixturesInInterpreterAndMultipass) {
  const auto FixtureDir = getLegacyReproFixtureDir();
  const std::vector<std::pair<std::string, uint64_t>> FixtureFiles = {
      {"block_254277_tx_0.json", 57956},
      {"block_254297_tx_0.json", 94849},
  };

  for (const auto &[Name, CanonicalTxGas] : FixtureFiles) {
    SCOPED_TRACE(Name);
    ParsedFixture Fixture = loadFixture(FixtureDir / Name);
    ASSERT_TRUE(Fixture.IsValid);
    EXPECT_EQ(Fixture.ExpectedTxGas, CanonicalTxGas);

    {
      auto Result = runFixture(Fixture, common::RunMode::InterpMode);
      ASSERT_TRUE(Result.Success) << Result.ErrorMessage;
      assertExpectedStatus(Fixture.ExpectedStatus, Result.Status);
      EXPECT_GT(Result.GasCharged, 0U)
          << "fixture=" << Fixture.FixturePath << " mode=interpreter";
    }

#ifdef ZEN_ENABLE_MULTIPASS_JIT
    {
      auto Result = runFixture(Fixture, common::RunMode::MultipassMode);
      ASSERT_TRUE(Result.Success) << Result.ErrorMessage;
      assertExpectedStatus(Fixture.ExpectedStatus, Result.Status);
      EXPECT_GT(Result.GasCharged, 0U)
          << "fixture=" << Fixture.FixturePath << " mode=multipass";
    }
#endif
  }
}

#ifdef ZEN_ENABLE_LIBEVM
TEST(EVMLegacyCallReproTest, ExecuteFixturesViaDTVMApi) {
  const auto FixtureDir = getLegacyReproFixtureDir();
  const std::vector<std::string> FixtureFiles = {"block_254277_tx_0.json"};
  for (const auto &Name : FixtureFiles) {
    SCOPED_TRACE(Name);
    ParsedFixture Fixture = loadFixture(FixtureDir / Name);
    ASSERT_TRUE(Fixture.IsValid);
    auto RTInterp = runFixture(Fixture, common::RunMode::InterpMode);
    auto RTMulti = runFixture(Fixture, common::RunMode::MultipassMode);
    auto Interp = runFixtureViaDTVMApi(Fixture, "interpreter");
    auto Multi = runFixtureViaDTVMApi(Fixture, "multipass");
    ASSERT_TRUE(Interp.Success);
    ASSERT_TRUE(Multi.Success);
    EXPECT_EQ(Interp.Status, EVMC_SUCCESS);
    EXPECT_EQ(Multi.Status, EVMC_SUCCESS);
    EXPECT_EQ(Interp.GasCharged, Multi.GasCharged);
  }
}
#endif
