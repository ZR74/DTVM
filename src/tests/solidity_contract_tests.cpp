#include <cctype>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <map>
#include <rapidjson/document.h>
#include <rapidjson/istreamwrapper.h>
#include <string>
#include <vector>

#include <gtest/gtest.h>

#include "evm/interpreter.h"
#include "evm_test_helpers.h"
#include "evmc/mocked_host.hpp"
#include "host/evm/crypto.h"
#include "utils/others.h"
#include "zetaengine.h"
#include "evm/recursiveHost.hpp"

using namespace zen;
using namespace zen::evm;
using namespace zen::runtime;
using namespace zen::evm_test_utils;

namespace {
bool Debug = false;

std::string toLowerHex(const std::string &Hex) {
  std::string Result = Hex;
  for (char &C : Result) {
    C = std::tolower(static_cast<unsigned char>(C));
  }
  return Result;
}

bool hexEquals(const std::string &Hex1, const std::string &Hex2) {
  // std::string hex1 = toLowerHex(Hex1);
  // std::string hex2 = toLowerHex(Hex2);

  // // 先检查长度是否一致
  // if (hex1.size() != hex2.size()) {
  //     std::cout << "十六进制长度不匹配: " << hex1.size() << " vs " << hex2.size() << std::endl;
  //     return false;
  // }

  // bool isEqual = true;
  // // 逐字符对比并记录差异位置
  // for (size_t i = 0; i < hex1.size(); ++i) {
  //     if (hex1[i] != hex2[i]) {
  //         if (isEqual) { // 首次发现差异时输出标题
  //             std::cout << "十六进制差异位置：" << std::endl;
  //             isEqual = false;
  //         }
  //         // 输出差异位置（按字节索引，每2个字符代表1个字节）
  //         size_t byteIndex = i ;
  //         std::cout << "  字节索引 " << byteIndex 
  //                   << " (字符位置 " << i << "): " 
  //                   << hex1[i] << " vs " << hex2[i] << std::endl;
  //     }
  // }

  return toLowerHex(Hex1) == toLowerHex(Hex2);
}

std::string computeFunctionSelector(const std::string &FunctionSig) {
  const std::vector<uint8_t> InputBytes(FunctionSig.begin(), FunctionSig.end());

  const std::vector<uint8_t> Hash = host::evm::crypto::keccak256(InputBytes);

  if (Hash.size() >= 4) {
    return utils::toHex(Hash.data(), 4);
  }

  return "";
}

struct SolidityTestCase {
  std::string Name;
  std::string Function;
  std::string Expected;
  std::string Contract;
  std::string Calldata;
};

struct SolcContractData {
  std::string DeployBytecode;
  std::string RuntimeBytecode;
};

struct ContractInstance {
  EVMInstance *Instance;
  evmc::address Address; 
};

struct SolidityContractTestData {
  std::string ContractPath;
  std::vector<SolidityTestCase> TestCases;
  std::map<std::string, SolcContractData> ContractDataMap;
  std::string MainContract;
  std::vector<std::string> DeployContracts;
  // 直接存储解析后的构造函数参数（合约名 -> 列表<(类型, 值)>）
  std::map<std::string, std::vector<std::pair<std::string, std::string>>> constructor_args;
};

std::map<std::string, SolcContractData>
loadAllSolcContractData(const std::string &JsonPath) {
  std::map<std::string, SolcContractData> ContractDataMap;
  std::ifstream File(JsonPath);
  if (!File.is_open()) {
    return ContractDataMap;
  }

  rapidjson::IStreamWrapper Isw(File);
  rapidjson::Document Doc;
  Doc.ParseStream(Isw);

  if (Doc.HasParseError()) {
    return ContractDataMap;
  }

  if (!Doc.HasMember("contracts") || !Doc["contracts"].IsObject()) {
    return ContractDataMap;
  }

  const auto &Contracts = Doc["contracts"].GetObject();
  if (Contracts.MemberCount() == 0) {
    return ContractDataMap;
  }

  for (const auto &ContractEntry : Contracts) {
    std::string ContractFullName = ContractEntry.name.GetString();
    const auto &ContractInfo = ContractEntry.value;

    std::string ContractName = ContractFullName;
    if (size_t ColonPos = ContractFullName.find(':');
        ContractFullName.find(':') != std::string::npos) {
      ContractName = ContractFullName.substr(ColonPos + 1);
    }

    SolcContractData ContractData;

    if (ContractInfo.HasMember("bin") && ContractInfo["bin"].IsString()) {
      ContractData.DeployBytecode = ContractInfo["bin"].GetString();
    }

    if (ContractInfo.HasMember("bin-runtime") &&
        ContractInfo["bin-runtime"].IsString()) {
      ContractData.RuntimeBytecode = ContractInfo["bin-runtime"].GetString();
    }

    ContractDataMap[ContractName] = ContractData;
  }

  return ContractDataMap;
}

std::vector<SolidityContractTestData> getAllSolidityContractTests() {
  std::vector<SolidityContractTestData> Tests;
  std::filesystem::path DirPath =
      std::filesystem::path(__FILE__).parent_path() /
      std::filesystem::path("../../tests/evm_solidity");

  if (!std::filesystem::exists(DirPath)) {
    std::cerr << "tests/evm_solidity does not exist: " << DirPath.string()
              << std::endl;
    return Tests;
  }

  for (const auto &Entry : std::filesystem::directory_iterator(DirPath)) {
    if (Entry.is_directory()) {
      std::filesystem::path ContractDir = Entry.path();
      std::filesystem::path TestCasesFile = ContractDir / "test_cases.json";

      std::string FolderName = ContractDir.filename().string();

      if (std::filesystem::path SolcJsonFile =
              ContractDir / (FolderName + ".json");
          std::filesystem::exists(SolcJsonFile) &&
          std::filesystem::exists(TestCasesFile)) {
        SolidityContractTestData ContractTest;
        ContractTest.ContractPath = ContractDir.string();
        ContractTest.ContractDataMap =
            loadAllSolcContractData(SolcJsonFile.string());

        if (ContractTest.ContractDataMap.empty()) {
          continue;
        }

        if (std::ifstream File(TestCasesFile); File.is_open()) {
          rapidjson::IStreamWrapper Isw(File);
          rapidjson::Document Doc;
          Doc.ParseStream(Isw);

          if (!Doc.HasParseError()) {
            if (Doc.HasMember("main_contract") &&
                Doc["main_contract"].IsString()) {
              ContractTest.MainContract = Doc["main_contract"].GetString();
            } else {
              ContractTest.MainContract =
                  ContractTest.ContractDataMap.begin()->first;
            }

            if (Doc.HasMember("deploy_contracts") &&
                Doc["deploy_contracts"].IsArray()) {
              const auto &DeployContracts = Doc["deploy_contracts"].GetArray();
              for (const auto &Contract : DeployContracts) {
                if (Contract.IsString()) {
                  ContractTest.DeployContracts.push_back(Contract.GetString());
                }
              }
            } else {
              ContractTest.DeployContracts.push_back(ContractTest.MainContract);
            }

            if (Doc.HasMember("test_cases") && Doc["test_cases"].IsArray()) {
              const auto &TestCases = Doc["test_cases"].GetArray();
              for (const auto &TestCase : TestCases) {
                if (TestCase.HasMember("name") && TestCase["name"].IsString() &&
                    TestCase.HasMember("expected") &&
                    TestCase["expected"].IsString()) {

                  SolidityTestCase Test;
                  Test.Name = TestCase["name"].GetString();
                  Test.Expected = TestCase["expected"].GetString();

                  if (TestCase.HasMember("function") &&
                      TestCase["function"].IsString()) {
                    Test.Function = TestCase["function"].GetString();
                  }

                  if (TestCase.HasMember("calldata") &&
                      TestCase["calldata"].IsString()) {
                    Test.Calldata = TestCase["calldata"].GetString();
                  } else if (!Test.Function.empty()) {
                    std::string FunctionSelector =
                        computeFunctionSelector(Test.Function);
                    if (!FunctionSelector.empty()) {
                      Test.Calldata = FunctionSelector;
                    } else {
                      // Skip test case if we can't compute calldata
                      continue;
                    }
                  } else {
                    // Skip test case if neither calldata nor function provided
                    continue;
                  }

                  if (TestCase.HasMember("contract") &&
                      TestCase["contract"].IsString()) {
                    Test.Contract = TestCase["contract"].GetString();
                  } else {
                    Test.Contract = ContractTest.MainContract;
                  }
                  ContractTest.TestCases.push_back(Test);
                }
              }
            }
            // 核心修改：解析 constructor_args 并存储到结构体（不再保留 Doc）
            if (Doc.HasMember("constructor_args") && Doc["constructor_args"].IsObject()) {
              const auto &ctor_args_obj = Doc["constructor_args"].GetObject();
              for (const auto &entry : ctor_args_obj) {
                std::string contract_name = entry.name.GetString();
                if (entry.value.IsArray()) {
                  std::vector<std::pair<std::string, std::string>> args;
                  for (const auto &arg : entry.value.GetArray()) {
                    if (arg.HasMember("type") && arg["type"].IsString() &&
                        arg.HasMember("value") && arg["value"].IsString()) {
                      args.emplace_back(
                        arg["type"].GetString(),
                        arg["value"].GetString()
                      );
                    }
                  }
                  ContractTest.constructor_args[contract_name] = args;
                }
              }
            }
          }
          File.close();
        }

        // Validate main contract exists and has required data
        auto MainContractIt =
            ContractTest.ContractDataMap.find(ContractTest.MainContract);
        if (MainContractIt != ContractTest.ContractDataMap.end() &&
            !MainContractIt->second.DeployBytecode.empty() &&
            !MainContractIt->second.RuntimeBytecode.empty() &&
            !ContractTest.TestCases.empty()) {
          Tests.push_back(ContractTest);
        }
      }
    }
  }
  
  return Tests;
}
// 辅助函数：将参数编码为Solidity ABI格式
std::string encodeAbiParam(
    const std::string& type, 
    const std::string& value, 
    const std::map<std::string, evmc::address>& deployed_addrs) {
  
  if (type == "address") {
    auto it = deployed_addrs.find(value);
    if (it != deployed_addrs.end()) {
      std::string encoded = "000000000000000000000000" + utils::toHex(it->second.bytes, 20);
      // std::cout << "编码地址参数：" << value << " → " << encoded << std::endl;  // 新增打印
      return encoded;
    } else {
      std::string addr_hex = (value.substr(0, 2) == "0x") ? value.substr(2) : value;
      std::string encoded = "000000000000000000000000" + addr_hex;
      // std::cout << "未找到合约名称 " << value << "，编码为：" << encoded << std::endl;  // 新增打印
      return encoded;
    }
  }
  else if (type == "uint256") {
    std::string uint_hex = (value.substr(0, 2) == "0x") ? value.substr(2) : value;
    return std::string(64 - uint_hex.size(), '0') + uint_hex;
  }
  throw std::invalid_argument("Unsupported ABI type: " + type);
}
// 工具函数：检测是否为库合约字节码（开头为73+20字节全0）
bool isLibraryBytecode(const std::string& hex) {
  // 库合约占位符特征：前42字符为 "73" + 40个0（20字节全0）
  return hex.size() >= 42 
      && hex.substr(0, 2) == "73"  // 开头是PUSH20指令
      && hex.substr(2, 40) == std::string(40, '0');  // 后续20字节全0
}

// 工具函数：用实际地址替换库合约的占位符
std::string replaceLibraryPlaceholder(const std::string& expectedHex, const std::string& actualHex) {
  if (expectedHex.size() < 42 || actualHex.size() < 42) {
    return expectedHex;  // 长度不足，不处理
  }
  // 提取实际地址（actualHex中73后的20字节，40个十六进制字符）
  std::string actualAddress = actualHex.substr(2, 40);
  // 替换预期字节码中的占位符（保留73，替换后续40个0为实际地址）
  return "73" + actualAddress + expectedHex.substr(42);
}

} // namespace

class SolidityContractTest
    : public testing::TestWithParam<SolidityContractTestData> {};

TEST_P(SolidityContractTest, ExecuteContractSequence) {
  const auto &ContractTest = GetParam();

  std::string ContractName =
      std::filesystem::path(ContractTest.ContractPath).filename().string();
  if (Debug)
    std::cout << "\n=== Testing contract: " << ContractName
              << " ===" << std::endl;

  RuntimeConfig Config;
  Config.Mode = common::RunMode::InterpMode;
  // Create temporary MockedHost first for Runtime creation
  auto TempMockedHost = std::make_unique<evmc::MockedHost>();
  auto RT = Runtime::newEVMRuntime(Config, TempMockedHost.get());
  ASSERT_TRUE(RT!=nullptr)<<"Failed to create runtime";

  // Create Isolation for recursive host
  Isolation *IsoForRecursive = RT->createManagedIsolation();
  ASSERT_TRUE(IsoForRecursive!=nullptr)<<"Failed to create Isolation for recursive host";
  // Now create RecursiveHost with Runtime and Isolation references
  auto RecursiveHostPtr =
      std::make_unique<RecursiveHost>(RT.get(), IsoForRecursive);
  RecursiveHost *MockedHost = RecursiveHostPtr.get();

  // Copy accounts and context from temporary host
  MockedHost->accounts = TempMockedHost->accounts;
  MockedHost->tx_context = TempMockedHost->tx_context;

  // Switch to using RecursiveHost
  std::unique_ptr<evmc::Host> Host = std::move(RecursiveHostPtr);
  uint8_t deployer_bytes[20] = {0x10, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
                             0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00};
  evmc::address deployer_addr;
  // 直接使用数组地址，而非.begin()
  std::copy(std::begin(deployer_bytes), std::end(deployer_bytes), deployer_addr.bytes);

  // 确保部署者账户在Host中存在并初始化nonce
  auto& deployer_account = MockedHost->accounts[deployer_addr];  // 若不存在会自动创建
  deployer_account.nonce = 0;  // 显式初始化nonce为0（首次部署用）
  deployer_account.set_balance(100000000UL);  // 初始化足够的余额（可选，视测试需求）

  uint64_t GasLimit = 100000000UL;
  std::map<std::string, ContractInstance> DeployedContracts;

  // Step 1: Deploy all specified contracts
  std::map<std::string, evmc::address> deployed_addresses;
  for (const std::string &NowContractName : ContractTest.DeployContracts) {
    // std::cout<<"部署合约名："<<NowContractName<<std::endl;
    auto ContractIt = ContractTest.ContractDataMap.find(NowContractName);
    ASSERT_NE(ContractIt, ContractTest.ContractDataMap.end())
        << "Contract not found: " << NowContractName;

    const auto &[ContractAddress, ContractData] = *ContractIt;
    // 核心修改：直接从结构体获取构造函数参数（不再解析 Doc）
    std::vector<std::pair<std::string, std::string>> ctor_args;
    auto args_it = ContractTest.constructor_args.find(NowContractName);  // 使用.访问成员
    if (args_it != ContractTest.constructor_args.end()) {
      ctor_args = args_it->second;
    }

    // 拼接部署字节码 + 构造函数参数
    std::string deploy_hex = ContractData.DeployBytecode;
    for (const auto &[type, value] : ctor_args) {
      deploy_hex += encodeAbiParam(type, value, deployed_addresses);
    }
    // std::cout << "部署字节码+参数: " << deploy_hex << std::endl;

    if (Debug)
      std::cout << "Deploying contract: " << NowContractName << std::endl;

    ASSERT_FALSE(ContractData.DeployBytecode.empty())
        << "Deploy bytecode is empty for " << NowContractName;

    auto DeployBytecode = utils::fromHex(deploy_hex);
    ASSERT_TRUE(DeployBytecode) << "Failed to convert deploy hex to bytecode";

    TempHexFile TempDeployFile(ContractTest.ContractPath,
                               "temp_deploy_" + NowContractName,
                               deploy_hex);

    auto DeployModRet = RT->loadEVMModule(TempDeployFile.getPath());
    ASSERT_TRUE(DeployModRet)
        << "Failed to load deploy module for " << NowContractName;

    EVMModule *DeployMod = *DeployModRet;
    Isolation *DeployIso = RT->createManagedIsolation();
    ASSERT_TRUE(DeployIso) << "Failed to create deploy isolation for "
                           << NowContractName;

    auto DeployInstRet = DeployIso->createEVMInstance(*DeployMod, GasLimit);
    ASSERT_TRUE(DeployInstRet)
        << "Failed to create deploy instance for " << NowContractName;

    EVMInstance *DeployInst = *DeployInstRet;
    InterpreterExecContext DeployCtx(DeployInst);
    BaseInterpreter DeployInterpreter(DeployCtx);
    
    // 新增：计算新合约地址（关键步骤）
    evmc::address new_contract_addr = MockedHost->compute_create_address(deployer_addr, deployer_account.nonce);
    // std::cout << "部署生成地址: 0x" << utils::toHex(new_contract_addr.bytes, 20) << std::endl;

    evmc_message Msg = {
        .kind = EVMC_CREATE,
        .flags = 0,
        .depth = 0,
        .gas = (long)GasLimit,
        .recipient = new_contract_addr,  
        .sender = deployer_addr,
    };
    DeployCtx.allocFrame(&Msg);
    // Set the host for the execution frame
    auto *Frame = DeployCtx.getCurFrame();
    Frame->Host = MockedHost;

    EXPECT_NO_THROW({ DeployInterpreter.interpret(); })
        << "Deploy failed for " << NowContractName;

    const auto &DeployResult = DeployCtx.getReturnData();
    ASSERT_FALSE(DeployResult.empty())
        << "Deploy should return runtime code for " << NowContractName;

    std::string DeployResultHex =
        utils::toHex(DeployResult.data(), DeployResult.size());
    // std::cout << "加载的部署字节码DeployResultHex: " << DeployResultHex << std::endl;
    // std::cout << "预期的运行时字节码RuntimeBytecode: " << ContractData.RuntimeBytecode << std::endl;
    if (Debug) {
      std::cout << "Deploy result hex: " << DeployResultHex << std::endl;
      std::cout << "Expected runtime bytecode: " << ContractData.RuntimeBytecode
                << std::endl;
    }
    std::string adjustedRuntimeBytecode = ContractData.RuntimeBytecode;
    if (isLibraryBytecode(adjustedRuntimeBytecode)) {
      adjustedRuntimeBytecode = replaceLibraryPlaceholder(adjustedRuntimeBytecode, DeployResultHex);
    }
    ASSERT_TRUE(hexEquals(DeployResultHex, adjustedRuntimeBytecode))
        << "Deploy result does not match runtime bytecode for "
        << NowContractName;

    TempHexFile TempRuntimeFile(ContractTest.ContractPath,
                                "temp_runtime_" + NowContractName,
                                DeployResultHex);

    auto CallModRet = RT->loadEVMModule(TempRuntimeFile.getPath());
    ASSERT_TRUE(CallModRet)
        << "Failed to load runtime module for " << NowContractName;

    EVMModule *CallMod = *CallModRet;
    Isolation *CallIso = RT->createManagedIsolation();
    ASSERT_TRUE(CallIso) << "Failed to create runtime isolation for "
                         << NowContractName;

    auto CallInstRet = CallIso->createEVMInstance(*CallMod, GasLimit);
    ASSERT_TRUE(CallInstRet)
        << "Failed to create runtime instance for " << NowContractName;

    EVMInstance *CallInst = *CallInstRet;

    // DeployedContracts[NowContractName] = {CallInst};
    
    // 部署后，将地址与实例关联存储
    DeployedContracts[NowContractName] = {CallInst, new_contract_addr};
    // 1. 将部署生成的runtime字节码写入新合约账户
    auto& new_contract_account = MockedHost->accounts[new_contract_addr];
    new_contract_account.code = std::basic_string<uint8_t, evmc::byte_traits<uint8_t>>(
        DeployResult.begin(), 
        DeployResult.end()
    );
    // 计算代码哈希（得到 vector<uint8_t>）
    const std::vector<uint8_t> code_hash_vec = host::evm::crypto::keccak256 (DeployResult);

    // 确保哈希长度正确（keccak256 哈希固定为 32 字节）
    assert (code_hash_vec.size () == 32 && "Keccak256 hash must be 32 bytes");

    // 将 vector 转换为 evmc::bytes32
    evmc::bytes32 code_hash;
    std::memcpy (code_hash.bytes, code_hash_vec.data (), 32); // 直接复制 32 字节到 bytes 数组

    // 赋值给 codehash
    new_contract_account.codehash = code_hash;
    new_contract_account.nonce = 1;  // 新合约初始nonce为1（部署后默认为1）
    // 2. 更新部署者的nonce（部署一次nonce+1，确保下次部署地址正确）
    deployer_account.nonce += 1;
    deployed_addresses[NowContractName] = new_contract_addr;

    // // 打印编译时的预期字节码（前32字节）
    // std::cout << "[预期] Caller 字节码前32字节: 0x" << ContractData.RuntimeBytecode.substr(0, 64) << std::endl;

    // // 打印实际部署的 Caller 字节码（前32字节）
    // auto& caller_account = MockedHost->accounts[new_contract_addr];
    // std::cout << "[实际] 部署的 Caller 字节码前32字节: 0x" << utils::toHex(caller_account.code.data(), 32) << std::endl;


    if (Debug)
      std::cout << "✓ Contract " << NowContractName << " deployed successfully"
                << std::endl;
  }
  // 部署所有合约后添加
  std::cout << "部署的合约地址映射：" << std::endl;
  for (const auto& [name, addr] : deployed_addresses) {
    std::cout << "  " << name << " → 0x" << utils::toHex(addr.bytes, 20) << std::endl;
  }
  // 部署 Callee 后，读取其 slot 0 的值
  evmc::address callee_addr = deployed_addresses["CalleeContract"];
  auto& callee_account = MockedHost->accounts[callee_addr];
  evmc::bytes32 x_slot = evmc::bytes32{}; // slot 0
  evmc::bytes32 x_value = MockedHost->get_storage(callee_addr, x_slot);
  std::cout << "[Callee 初始 x] slot 0 值: 0x" << utils::toHex(x_value.bytes, 32) << std::endl;

  // Step 2: Execute all test cases
  for (size_t I = 0; I < ContractTest.TestCases.size(); ++I) {
    const auto &TestCase = ContractTest.TestCases[I];
    std::cout << "Now Testcase Function: " << TestCase.Function << std::endl;

    if (Debug)
      std::cout << "\n--- Test " << (I + 1) << "/"
                << ContractTest.TestCases.size() << ": " << TestCase.Name
                << " (Contract: " << TestCase.Contract << ") ---" << std::endl;

    auto InstanceIt = DeployedContracts.find(TestCase.Contract);
    ASSERT_NE(InstanceIt, DeployedContracts.end())
        << "Contract instance not found: " << TestCase.Contract;

    const auto &ContractInstance = InstanceIt->second;
    // std::cout << "实际调用的地址: 0x" << utils::toHex(ContractInstance.Address.bytes, 20) << std::endl;

    InterpreterExecContext CallCtx(ContractInstance.Instance);

    ASSERT_FALSE(TestCase.Calldata.empty())
        << "Calldata must be provided for test: " << TestCase.Name;

    auto Calldata = utils::fromHex(TestCase.Calldata);
    std::cout<<"TestCase.Calldata:"<<TestCase.Calldata<<std::endl;
    for (size_t i = 0; i < Calldata->size(); ++i) {
        // 每个字节转换为两位十六进制，不足两位补前导零
        std::cout << std::hex << std::setw(2) << std::setfill('0') 
                  << static_cast<int>(Calldata->data()[i]);
    }
    std::cout << std::dec << std::endl; // 恢复十进制输出格式

    evmc_message Msg = {
        .kind = EVMC_CALL,
        .flags = 0,
        .depth = 0,
        .gas = (long)GasLimit,
        .recipient = ContractInstance.Address,
        .input_data = Calldata->data(),
        .input_size = Calldata->size(),
    };
    // 打印 input_data 的十六进制内容
    std::cout << "[调试] input_data (calldata) 内容: 0x";
    for (size_t i = 0; i < Msg.input_size; ++i) {
        // 每个字节转换为两位十六进制，不足两位补前导零
        std::cout << std::hex << std::setw(2) << std::setfill('0') 
                  << static_cast<int>(Msg.input_data[i]);
    }
    std::cout << std::dec << std::endl; // 恢复十进制输出格式

    CallCtx.allocFrame(&Msg);
    // Set the host for the execution frame
    auto *Frame = CallCtx.getCurFrame();
    Frame->Host = MockedHost;

    BaseInterpreter CallInterpreter(CallCtx);
    EXPECT_NO_THROW({ CallInterpreter.interpret(); })
        << "Function call failed: " << TestCase.Function;

    const auto &CallResult = CallCtx.getReturnData();
    std::string ResultHex = utils::toHex(CallResult.data(), CallResult.size());

    if (Debug) {
      if (!TestCase.Function.empty()) {
        std::cout << "Function: " << TestCase.Function << std::endl;
      }
      std::cout << "Expected: " << TestCase.Expected << std::endl;
      std::cout << "Actual:   " << ResultHex << std::endl;
    }

    EXPECT_TRUE(hexEquals(ResultHex, TestCase.Expected))
        << "Test case failed: " << TestCase.Name
        << (!TestCase.Function.empty() ? "\nFunction: " + TestCase.Function
                                       : "")
        << "\nExpected: " << TestCase.Expected << "\nActual:   " << ResultHex;

    if (!hexEquals(ResultHex, TestCase.Expected)) {
      std::cout << "✗ FAILED" << std::endl;
    }
  }

  if (Debug)
    std::cout << "\n=== Contract " << ContractName << " testing completed ===\n"
              << std::endl;
}

struct SolidityTestNameGenerator {
  std::string operator()(
      const testing::TestParamInfo<SolidityContractTestData> &Info) const {
    const auto &ContractTest = Info.param;
    std::string ContractName =
        std::filesystem::path(ContractTest.ContractPath).filename().string();
    return ContractName;
  }
};

auto SolidityTests = getAllSolidityContractTests();
INSTANTIATE_TEST_SUITE_P(
    SolidityContracts, SolidityContractTest,
    ::testing::ValuesIn(
        SolidityTests.empty()
            ? std::vector<SolidityContractTestData>{{SolidityContractTestData{
                  "", {}, {}, "", {},{}}}}
            : SolidityTests),
    SolidityTestNameGenerator{});
