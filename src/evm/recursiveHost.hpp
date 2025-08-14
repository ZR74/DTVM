// recursive_host.cpp
// Copyright (C) 2025 the DTVM authors. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0
#include "evmc/mocked_host.hpp"
#include "evm/interpreter.h"
#include "tests/evm_test_helpers.h"  // 包含TempHexFile的定义
#include "utils/others.h"      // 包含zen::utils::toHex
#include "runtime/runtime.h"
#include "runtime/isolation.h"
#include "host/evm/crypto.h"
#include "host/evm/keccak/keccak.hpp"
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

public:
  RecursiveHost(Runtime *RT, Isolation *Iso) : RT(RT), Iso(Iso) {}

  evmc::Result call(const evmc_message &Msg) noexcept override {
    // 1. 打印当前调用的基本信息（选择器、目标地址）
    std::cout << "\n[RecursiveHost] 收到跨合约调用:" << std::endl;
    std::cout << "  目标地址: 0x" << zen::utils::toHex(Msg.recipient.bytes, 20) << std::endl;
    std::cout << "  调用选择器: 0x" << zen::utils::toHex(Msg.input_data, 4) << std::endl; // 前4字节是选择器
    std::cout << "  输入数据长度: " << Msg.input_size << " 字节" << std::endl;
    // First call the parent MockedHost to record the call
    evmc::Result ParentResult = evmc::MockedHost::call(Msg);
    //print Msg.recipient
    std::cout << "0x"; // 以太坊地址前缀
    // 遍历20字节，每个字节转换为2位十六进制
    for (uint8_t b : Msg.recipient.bytes) {
        // 设置宽度为2，不足补0，以十六进制输出
        std::cout << std::setw(2) << std::setfill('0') << std::hex << static_cast<int>(b);
    }
    std::cout << std::dec<<std::endl; // 恢复十进制输出，避免影响后续输出

    // Try to find the target contract
    auto It = accounts.find(Msg.recipient);
    if (It == accounts.end() || It->second.code.empty()) {
      // No contract found, return parent result
      std::cout<<"No contract found, return parent result"<<std::endl;
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
    // std::cout<<"This call: "<<HexCode<<std::endl;
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

      const auto &ReturnData = Ctx.getReturnData();
      if (!ReturnData.empty()) {
        Result.output_data = ReturnData.data();
        Result.output_size = ReturnData.size();
      }
      // // 在 RecursiveHost::call 中，执行 Interpreter.interpret() 后
      // std::string host_return = utils::toHex(ReturnData.data(), ReturnData.size());
      // std::cout << "[RecursiveHost] 收集到的返回数据: 0x" << host_return << std::endl;

      return Result;

    } catch (const std::exception &E) {
      // On error, return parent result
      std::cout << "Error in recursive call: " << E.what() << std::endl;
      return ParentResult;
    }
  }
  using hash256 = evmc::bytes32;
  hash256 keccak256(evmc::bytes_view data) noexcept
  {
      // 调用底层 ethash::keccak256(const uint8_t*, size_t)，并转换返回值类型
      hash256 result;
      auto hash_result = ethash::keccak256(data.data(), data.size());
      std::memcpy(&result, &hash_result, sizeof(result));
      return result;
  }
  evmc::address compute_create_address(const evmc::address& Sender, uint64_t SenderNonce) noexcept
  {
      static constexpr auto RLP_STR_BASE = 0x80;
      static constexpr auto RLP_LIST_BASE = 0xc0;
      static constexpr auto ADDRESS_SIZE = sizeof(Sender);
      static constexpr std::ptrdiff_t MAX_NONCE_SIZE = sizeof(SenderNonce);

      uint8_t buffer[ADDRESS_SIZE + MAX_NONCE_SIZE + 3];  // 3 for RLP prefix bytes.
      auto p = &buffer[1];                                // Skip RLP list prefix for now.
      *p++ = RLP_STR_BASE + ADDRESS_SIZE;                 // Set RLP string prefix for evmc::address.
      p = std::copy_n(Sender.bytes, ADDRESS_SIZE, p);

      if (SenderNonce < RLP_STR_BASE)  // Short integer encoding including 0 as empty string (0x80).
      {
          *p++ = SenderNonce != 0 ? static_cast<uint8_t>(SenderNonce) : RLP_STR_BASE;
      }
      else  // Prefixed integer encoding.
      {
          // TODO: bit_width returns int after [LWG 3656](https://cplusplus.github.io/LWG/issue3656).
          // NOLINTNEXTLINE(readability-redundant-casting)
          const auto num_nonzero_bytes = static_cast<int>((std::__bit_width(SenderNonce) + 7) / 8);
          *p++ = static_cast<uint8_t>(RLP_STR_BASE + num_nonzero_bytes);
          intx::be::unsafe::store(p, SenderNonce);
          size_t shift = MAX_NONCE_SIZE - num_nonzero_bytes;
          if (shift > 0) {
              for (size_t i = 0; i < MAX_NONCE_SIZE - shift; ++i) {
                  p[i] = p[i + shift];
              }
              p += MAX_NONCE_SIZE - shift;
          }
      }

      const auto total_size = static_cast<size_t>(p - buffer);
      buffer[0] = static_cast<uint8_t>(RLP_LIST_BASE + (total_size - 1));  // Set the RLP list prefix.

      const auto base_hash = keccak256({buffer, total_size});
      evmc::address addr;
      std::copy_n(&base_hash.bytes[sizeof(base_hash) - ADDRESS_SIZE], ADDRESS_SIZE, addr.bytes);
      return addr;
  }
  
  evmc::address compute_create2_address(
      const evmc::address& Sender, const evmc::bytes32& Salt, evmc::bytes_view Init_Code) noexcept
  {
      const auto init_code_hash = keccak256(Init_Code);
      uint8_t buffer[1 + sizeof(Sender) + sizeof(Salt) + sizeof(init_code_hash)];
      static_assert(std::size(buffer) == 85);
      auto it = std::begin(buffer);
      *it++ = 0xff;
      it = std::copy_n(Sender.bytes, sizeof(Sender), it);
      it = std::copy_n(Salt.bytes, sizeof(Salt), it);
      std::copy_n(init_code_hash.bytes, sizeof(init_code_hash), it);
      const auto base_hash = keccak256({buffer, std::size(buffer)});
      evmc::address addr;
      std::copy_n(&base_hash.bytes[sizeof(base_hash) - sizeof(addr)], sizeof(addr), addr.bytes);
      return addr;
  }
};

}  // namespace zen::evm
