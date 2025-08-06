// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract EnvInfoContract {
    function getContractAddress() external view returns (address) {
        return address(this);
    }

    function getBlockNumber() external view returns (uint256) {
        return block.number;
    }

    function getBlockTimestamp() external view returns (uint256) {
        return block.timestamp;
    }

    function getBlockDifficulty() external view returns (uint256) {
        return block.prevrandao;
    }

    function getChainId() external view returns (uint256) {
        return block.chainid;
    }

    function getCallerAddress() external view returns (address) {
        return msg.sender;
    }

    function getCallValue() external payable returns (uint256) {
        return msg.value;
    }
}
