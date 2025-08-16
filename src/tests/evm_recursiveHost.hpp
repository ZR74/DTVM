// recursive_host.cpp
// Copyright (C) 2025 the DTVM authors. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0
#include "evm/interpreter.h"
#include "evmc/mocked_host.hpp"
#include "host/evm/crypto.h"
#include "host/evm/keccak/keccak.hpp"
#include "runtime/isolation.h"
#include "runtime/runtime.h"
#include "tests/evm_test_helpers.h"
#include "utils/others.h"
#include <iostream>

using namespace zen;
using namespace zen::runtime;
using namespace zen::evm_test_utils;

namespace zen::evm {

/// Recursive Host that can execute CALL instructions by creating new
/// interpreters
class RecursiveHost : public evmc::MockedHost {
private:
  Runtime *RT = nullptr;
  Isolation *Iso = nullptr;
  std::vector<uint8_t> ReturnData;

public:
  RecursiveHost(Runtime *RT, Isolation *Iso) : RT(RT), Iso(Iso) {}

  evmc::Result call(const evmc_message &Msg) noexcept override {
    evmc::Result ParentResult = evmc::MockedHost::call(Msg);
    // Try to find the target contract
    auto It = accounts.find(Msg.recipient);
    if (It == accounts.end() || It->second.code.empty()) {
      // No contract found, return parent result
      std::cout << "No contract found, return parent result" << std::endl;
      return ParentResult;
    }

    try {
      // Create temporary hex file from contract code using RAII
      std::string HexCode = "0x" + zen::utils::toHex(It->second.code.data(),
                                                     It->second.code.size());
      TempHexFile TempFile(HexCode);
      if (!TempFile.isValid()) {
        return ParentResult;
      }
      // Load EVM module
      auto ModRet = RT->loadEVMModule(TempFile.getPath());
      if (!ModRet) {
        return ParentResult;
      }

      EVMModule *Mod = *ModRet;

      // Create EVM instance
      auto InstRet = Iso->createEVMInstance(*Mod, Msg.gas);
      if (!InstRet) {
        return ParentResult;
      }

      EVMInstance *Inst = *InstRet;

      // Create interpreter context and execute
      InterpreterExecContext Ctx(Inst);
      BaseInterpreter Interpreter(Ctx);

      evmc_message CallMsg = Msg;
      Ctx.allocFrame(&CallMsg);

      // Set the host for the execution frame
      auto *Frame = Ctx.getCurFrame();
      Frame->Host = this;

      // Execute the interpreter
      Interpreter.interpret();

      // Create result based on execution status
      evmc::Result Result;
      Result.status_code = Ctx.getStatus();
      Result.gas_left = CallMsg.gas;

      ReturnData = Ctx.getReturnData();
      if (!ReturnData.empty()) {
        Result.output_data = ReturnData.data();
        Result.output_size = ReturnData.size();
      }
      return Result;

    } catch (const std::exception &E) {
      // On error, return parent result
      std::cout << "Error in recursive call: " << E.what() << std::endl;
      return ParentResult;
    }
  }
  using hash256 = evmc::bytes32;
  hash256 keccak256(evmc::bytes_view data) noexcept {
    // Call the underlying layer ethash::keccak256(const uint8_t*, size_t),and
    // convert the return value type
    hash256 result;
    auto hash_result = ethash::keccak256(data.data(), data.size());
    std::memcpy(&result, &hash_result, sizeof(result));
    return result;
  }
  evmc::address computeCreateAddress(const evmc::address &Sender,
                                     uint64_t SenderNonce) noexcept {
    static constexpr auto RLP_STR_BASE = 0x80;
    static constexpr auto RLP_LIST_BASE = 0xc0;
    static constexpr auto ADDRESS_SIZE = sizeof(Sender);
    static constexpr std::ptrdiff_t MAX_NONCE_SIZE = sizeof(SenderNonce);

    uint8_t
        Buffer[ADDRESS_SIZE + MAX_NONCE_SIZE + 3]; // 3 for RLP prefix bytes.
    auto P = &Buffer[1]; // Skip RLP list prefix for now.
    *P++ =
        RLP_STR_BASE + ADDRESS_SIZE; // Set RLP string prefix for evmc::address.
    P = std::copy_n(Sender.bytes, ADDRESS_SIZE, P);

    if (SenderNonce < RLP_STR_BASE) // Short integer encoding including 0 as
                                    // empty string (0x80).
    {
      *P++ =
          SenderNonce != 0 ? static_cast<uint8_t>(SenderNonce) : RLP_STR_BASE;
    } else // Prefixed integer encoding.
    {
      // TODO: bit_width returns int after [LWG
      // 3656](https://cplusplus.github.io/LWG/issue3656).
      // NOLINTNEXTLINE(readability-redundant-casting)
      const auto numNonzeroBytes =
          static_cast<int>((std::__bit_width(SenderNonce) + 7) / 8);
      *p++ = static_cast<uint8_t>(RLP_STR_BASE + numNonzeroBytes);
      intx::be::unsafe::store(P, SenderNonce);
      size_t Shift = MAX_NONCE_SIZE - numNonzeroBytes;
      if (Shift > 0) {
        for (size_t I = 0; I < MAX_NONCE_SIZE - Shift; ++I) {
          P[I] = P[I + shift];
        }
        P += MAX_NONCE_SIZE - shift;
      }
    }

    const auto totalSize = static_cast<size_t>(P - Buffer);
    Buffer[0] = static_cast<uint8_t>(
        RLP_LIST_BASE + (totalSize - 1)); // Set the RLP list prefix.

    const auto baseHash = keccak256({Buffer, totalSize});
    evmc::address Addr;
    std::copy_n(&baseHash.bytes[sizeof(baseHash) - ADDRESS_SIZE], ADDRESS_SIZE,
                Addr.bytes);
    return Addr;
  }
};

} // namespace zen::evm
