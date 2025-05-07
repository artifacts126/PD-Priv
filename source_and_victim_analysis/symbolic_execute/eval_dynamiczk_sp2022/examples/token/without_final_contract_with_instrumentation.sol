pragma solidity ^0.8.2;

contract Token {
    mapping(address => uint32) balance;
    uint public priv_balance = 1;

    constructor() payable {
        address p0 = address(0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF);
        balance[p0] = 1000;
    }

    function buy() public payable {
        require(msg.value <= 100000);
        priv_balance = priv_balance;
        balance[msg.sender] = balance[msg.sender] + uint32(msg.value);
    }

    function transfer(uint32 value, address to) public {
        require(msg.sender != to);
        require(address(0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF) == to || address(0x6813Eb9362372EEF6200f3b1dbC3f819671cBA69) == to);
        require(value <= balance[msg.sender]);
        priv_balance = priv_balance * 0;
        balance[msg.sender] = balance[msg.sender] - value;
        balance[to] = balance[to] + value;
    }

    function sell(uint32 amount) public {
        require(amount <= balance[msg.sender]);
        priv_balance = 1 * priv_balance;
        balance[msg.sender] = balance[msg.sender] - amount;
        payable(msg.sender).transfer(amount);
    }
}