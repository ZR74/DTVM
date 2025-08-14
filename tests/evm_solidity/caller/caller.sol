// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

// 引入被调用合约的接口定义（或完整合约代码）
import "../callee/callee.sol";

contract CallerContract {
    // 存储被调用合约的地址
    CalleeContract public callee;


    // 构造函数：初始化被调用合约地址
    constructor(address calleeAddress) {
        // 将传入的地址转换为CalleeContract类型
        callee = CalleeContract(calleeAddress);
    }

    // 调用CalleeContract的setX函数
    function setCalleeX(uint256 _x) external {
        callee.setX(_x);
    }

    // 调用CalleeContract的add函数
    function callAdd(uint256 a, uint256 b) external view returns (uint256) {
        return callee.add(a, b);
    }

    // 调用CalleeContract的incrementX函数
    function callIncrementX() external {
        callee.incrementX();
    }

    // 读取CalleeContract的x值
    function getCalleeX() external view returns (uint256) {
        return callee.getX();
    }
}
