// Copyright (C) 2025 the DTVM authors. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

#include "evm_test_helpers.h"
#include "host/evm/crypto.h"
#include "mpt/merkle_patricia_trie.h"

#include <algorithm>
#include <evmc/hex.hpp>
#include <iostream>

namespace zen {
namespace test_utils {

namespace {

// RLP encoding functions for logs hash calculation
// These functions implement the Recursive Length Prefix encoding standard
// used in Ethereum for serializing data structures
std::vector<uint8_t> rlpEncodeLength(size_t Length, uint8_t Offset) {
  std::vector<uint8_t> Result;
  if (Length < 56) {
    Result.push_back(static_cast<uint8_t>(Offset + Length));
  } else {
    std::vector<uint8_t> LengthBytes;
    size_t TempLength = Length;
    while (TempLength > 0) {
      LengthBytes.push_back(static_cast<uint8_t>(TempLength & 0xFF));
      TempLength >>= 8;
    }
    std::reverse(LengthBytes.begin(), LengthBytes.end());
    Result.push_back(static_cast<uint8_t>(Offset + 55 + LengthBytes.size()));
    Result.insert(Result.end(), LengthBytes.begin(), LengthBytes.end());
  }
  return Result;
}

std::vector<uint8_t> rlpEncodeBytes(const std::vector<uint8_t> &Data) {
  if (Data.size() == 1 && Data[0] < 0x80) {
    return Data;
  }
  auto Header = rlpEncodeLength(Data.size(), 0x80);
  Header.insert(Header.end(), Data.begin(), Data.end());
  return Header;
}

std::vector<uint8_t>
rlpEncodeList(const std::vector<std::vector<uint8_t>> &Items) {
  std::vector<uint8_t> EncodedData;
  for (const auto &Item : Items) {
    EncodedData.insert(EncodedData.end(), Item.begin(), Item.end());
  }
  auto Header = rlpEncodeLength(EncodedData.size(), 0xc0);
  Header.insert(Header.end(), EncodedData.begin(), EncodedData.end());
  return Header;
}

std::string
calculateLogsHashImpl(const std::vector<evmc::MockedHost::log_record> &Logs) {
  std::vector<std::vector<uint8_t>> EncodedLogs;

  for (const auto &Log : Logs) {
    std::vector<std::vector<uint8_t>> LogComponents;

    std::vector<uint8_t> AddressBytes(Log.creator.bytes,
                                      Log.creator.bytes + 20);
    LogComponents.push_back(rlpEncodeBytes(AddressBytes));

    std::vector<std::vector<uint8_t>> TopicsEncoded;
    for (const auto &Topic : Log.topics) {
      std::vector<uint8_t> TopicBytes(Topic.bytes, Topic.bytes + 32);
      TopicsEncoded.push_back(rlpEncodeBytes(TopicBytes));
    }
    LogComponents.push_back(rlpEncodeList(TopicsEncoded));

    std::vector<uint8_t> DataBytes(Log.data.begin(), Log.data.end());
    LogComponents.push_back(rlpEncodeBytes(DataBytes));

    EncodedLogs.push_back(rlpEncodeList(LogComponents));
  }

  auto RlpEncodedLogs = rlpEncodeList(EncodedLogs);

  auto Hash = zen::host::evm::crypto::keccak256(RlpEncodedLogs);

  evmc::bytes_view HashView(
      reinterpret_cast<const unsigned char *>(Hash.data()), Hash.size());
  return evmc::hex(HashView);
}

// RLP encoding functions for state root calculation
// These are separate implementations optimized for account state encoding
std::vector<uint8_t> encodeRLPLength(size_t Length, uint8_t Offset) {
  std::vector<uint8_t> Result;

  if (Length < 56) {
    Result.push_back(static_cast<uint8_t>(Length + Offset));
  } else {
    std::vector<uint8_t> LengthBytes;
    size_t Temp = Length;
    while (Temp > 0) {
      LengthBytes.insert(LengthBytes.begin(),
                         static_cast<uint8_t>(Temp & 0xFF));
      Temp >>= 8;
    }
    Result.push_back(static_cast<uint8_t>(LengthBytes.size() + Offset + 55));
    Result.insert(Result.end(), LengthBytes.begin(), LengthBytes.end());
  }

  return Result;
}

std::vector<uint8_t> encodeRLPString(const std::vector<uint8_t> &Input) {
  if (Input.empty()) {
    return {0x80};
  }

  if (Input.size() == 1 && Input[0] < 0x80) {
    return Input;
  }

  auto LengthBytes = encodeRLPLength(Input.size(), 0x80);
  LengthBytes.insert(LengthBytes.end(), Input.begin(), Input.end());
  return LengthBytes;
}

std::vector<uint8_t>
encodeRLPList(const std::vector<std::vector<uint8_t>> &Items) {
  std::vector<uint8_t> Payload;
  for (const auto &Item : Items) {
    auto Encoded = encodeRLPString(Item);
    Payload.insert(Payload.end(), Encoded.begin(), Encoded.end());
  }

  auto LengthBytes = encodeRLPLength(Payload.size(), 0xc0);
  LengthBytes.insert(LengthBytes.end(), Payload.begin(), Payload.end());
  return LengthBytes;
}

std::vector<uint8_t> uint256beToBytes(const evmc::uint256be &Value) {
  const auto *Data = Value.bytes;
  size_t Start = 0;

  while (Start < sizeof(Value.bytes) && Data[Start] == 0) {
    Start++;
  }

  if (Start == sizeof(Value.bytes)) {
    return {};
  }

  return std::vector<uint8_t>(Data + Start, Data + sizeof(Value.bytes));
}

std::vector<uint8_t> calculateStorageRoot(
    const std::unordered_map<evmc::bytes32, evmc::StorageValue> &Storage) {
  zen::evm::mpt::MerklePatriciaTrie StorageTrie;

  for (const auto &[Key, StorageValue] : Storage) {
    bool IsEmpty = true;
    for (int I = 0; I < 32; I++) {
      if (StorageValue.current.bytes[I] != 0) {
        IsEmpty = false;
        break;
      }
    }
    if (IsEmpty)
      continue;

    auto KeyHash = zen::host::evm::crypto::keccak256(
        std::vector<uint8_t>(Key.bytes, Key.bytes + sizeof(Key.bytes)));

    auto ValueBytes = uint256beToBytes(StorageValue.current);
    auto EncodedValue = encodeRLPString(ValueBytes);

    StorageTrie.put(KeyHash, EncodedValue);
  }

  return StorageTrie.rootHash();
}

std::vector<uint8_t> encodeAccount(const evmc::MockedAccount &Account) {
  std::vector<std::vector<uint8_t>> AccountFields;

  if (Account.nonce == 0) {
    AccountFields.push_back({});
  } else {
    std::vector<uint8_t> NonceBytes;
    int Nonce = Account.nonce;
    while (Nonce > 0) {
      NonceBytes.insert(NonceBytes.begin(), static_cast<uint8_t>(Nonce & 0xFF));
      Nonce >>= 8;
    }
    AccountFields.push_back(NonceBytes);
  }

  auto BalanceBytes = uint256beToBytes(Account.balance);
  AccountFields.push_back(BalanceBytes);

  auto StorageRoot = calculateStorageRoot(Account.storage);
  AccountFields.push_back(StorageRoot);

  std::vector<uint8_t> CodeHash(Account.codehash.bytes,
                                Account.codehash.bytes +
                                    sizeof(Account.codehash.bytes));
  AccountFields.push_back(CodeHash);

  return encodeRLPList(AccountFields);
}

} // anonymous namespace

std::string
calculateLogsHash(const std::vector<evmc::MockedHost::log_record> &Logs) {
  return calculateLogsHashImpl(Logs);
}

bool verifyLogsHash(const std::vector<evmc::MockedHost::log_record> &Logs,
                    const std::string &ExpectedHash) {
  std::string CalculatedHash = "0x" + calculateLogsHash(Logs);
  if (CalculatedHash != ExpectedHash) {
    std::cout << "CalculatedLogsHash: " << CalculatedHash << std::endl;
    std::cout << "ExpectedLogsHash: " << ExpectedHash << std::endl;
  }
  return CalculatedHash == ExpectedHash;
}

bool verifyStateRoot(evmc::MockedHost &Host, const std::string &ExpectedHash) {
  zen::evm::mpt::MerklePatriciaTrie StateTrie;

  for (const auto &[Address, Account] : Host.accounts) {
    auto AddressHash = zen::host::evm::crypto::keccak256(std::vector<uint8_t>(
        Address.bytes, Address.bytes + sizeof(Address.bytes)));

    auto EncodedAccount = encodeAccount(Account);

    StateTrie.put(AddressHash, EncodedAccount);
  }

  auto StateRoot = StateTrie.rootHash();

  evmc::bytes_view HashView(StateRoot.data(), StateRoot.size());
  std::string CalculatedHash = "0x" + evmc::hex(HashView);

  if (CalculatedHash != ExpectedHash) {
    std::cout << "CalculatedRootHash: " << CalculatedHash << std::endl;
    std::cout << "ExpectedRootHash: " << ExpectedHash << std::endl;
  }

  return CalculatedHash == ExpectedHash;
}

} // namespace test_utils
} // namespace zen
