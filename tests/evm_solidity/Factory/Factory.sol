// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

// 被部署的目标合约（极简版）
contract SimpleContract {
    string public data; // 仅存储一个字符串数据

    // 构造函数：初始化数据
    constructor(string memory _data) {
        data = _data;
    }
}

// 部署工厂合约（仅负责部署SimpleContract）
contract SimpleFactory {
    // 存储所有部署的合约地址
    SimpleContract[] public deployedContracts;

    // 部署新合约的函数
    function deploy(string memory _data) external returns (SimpleContract) {
        // 核心逻辑：用new关键字部署合约，返回新合约实例
        SimpleContract newContract = new SimpleContract(_data);
        // 记录部署的合约（可选，便于追踪）
        deployedContracts.push(newContract);
        return newContract;
    }

    // 获取已部署合约的数量（可选）
    function getCount() external view returns (uint256) {
        return deployedContracts.length;
    }
}