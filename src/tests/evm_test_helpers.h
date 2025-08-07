// Copyright (C) 2025 the DTVM authors. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

#ifndef ZEN_TESTS_EVM_TEST_HELPERS_H
#define ZEN_TESTS_EVM_TEST_HELPERS_H

#include "evmc/mocked_host.hpp"

#include <filesystem>
#include <fstream>
#include <string>
#include <vector>

namespace zen {
namespace test_utils {

// RAII class for managing temporary hex files during testing
// This class automatically creates unique temporary files and cleans them up
// when the object goes out of scope. It provides move semantics to avoid
// accidental copying and premature cleanup.
//
// Usage relationship with other test components:
// 1. Test fixtures (StateTestFixture) contain bytecode as hex strings
// 2. EVM interpreter requires bytecode files for execution
// 3. TempHexFile bridges this gap by creating temporary files
// 4. Files are automatically cleaned up when test completes
//
// The move-only design ensures:
// - No accidental file duplication
// - Proper cleanup timing (only when original object destructs)
// - Exception safety during test execution
// - Clear ownership semantics in test code
class TempHexFile {
private:
  std::string FilePath;
  bool Valid = false;

public:
  // Creates a temporary hex file in the system temp directory
  explicit TempHexFile(const std::string &HexCode) {
    if (HexCode.empty() || HexCode == "0x") {
      return;
    }

    auto TempDir = std::filesystem::temp_directory_path();
    auto TempPath = TempDir / "dtvm_XXXXXX.hex";
    FilePath = TempPath.string();

    // Create unique filename
    auto BaseStr = TempPath.stem().string();
    auto Extension = TempPath.extension();
    for (int I = 0; I < 1000; ++I) {
      auto UniquePath =
          TempDir / (BaseStr + std::to_string(I) + Extension.string());
      if (!std::filesystem::exists(UniquePath)) {
        FilePath = UniquePath.string();
        break;
      }
    }

    std::string CleanHex = HexCode;
    if (CleanHex.size() >= 2 && CleanHex.substr(0, 2) == "0x") {
      CleanHex = CleanHex.substr(2);
    }

    std::ofstream File(FilePath);
    if (!File) {
      throw std::runtime_error("Failed to create temp file: " + FilePath);
    }
    File << CleanHex;
    File.close();
    Valid = true;
  }

  // Creates a temporary hex file at a specific location with custom suffix
  TempHexFile(const std::string &BasePath, const std::string &Suffix,
              const std::string &Content) {
    if (Content.empty()) {
      return;
    }

    FilePath = BasePath + "/" + Suffix + ".hex";

    std::ofstream File(FilePath);
    if (!File) {
      throw std::runtime_error("Failed to create temp file: " + FilePath);
    }
    File << Content;
    File.close();
    Valid = true;
  }

  // Automatically cleans up the temporary file
  ~TempHexFile() {
    if (Valid && !FilePath.empty()) {
      std::filesystem::remove(FilePath);
    }
  }

  // Move-only semantics to prevent accidental copying and double cleanup
  TempHexFile(const TempHexFile &) = delete;
  TempHexFile &operator=(const TempHexFile &) = delete;

  TempHexFile(TempHexFile &&Other) noexcept
      : FilePath(std::move(Other.FilePath)), Valid(Other.Valid) {
    Other.Valid = false;
  }

  TempHexFile &operator=(TempHexFile &&Other) noexcept {
    if (this != &Other) {
      if (Valid && !FilePath.empty()) {
        std::filesystem::remove(FilePath);
      }
      FilePath = std::move(Other.FilePath);
      Valid = Other.Valid;
      Other.Valid = false;
    }
    return *this;
  }

  bool isValid() const { return Valid; }
  const std::string &getPath() const { return FilePath; }
};

// Hash calculation and verification utilities for EVM state testing
// These functions implement the specific hashing algorithms required
// for verifying EVM state transitions and log outputs

// Calculates the RLP-encoded Keccak-256 hash of log records
std::string
calculateLogsHash(const std::vector<evmc::MockedHost::log_record> &Logs);

// Verifies that the given logs produce the expected hash
bool verifyLogsHash(const std::vector<evmc::MockedHost::log_record> &Logs,
                    const std::string &ExpectedHash);

// Verifies the state root hash by building a Merkle Patricia Trie
// from all accounts in the mocked host and comparing the root hash
bool verifyStateRoot(evmc::MockedHost &Host, const std::string &ExpectedHash);

} // namespace test_utils
} // namespace zen

#endif // ZEN_TESTS_EVM_TEST_HELPERS_H
