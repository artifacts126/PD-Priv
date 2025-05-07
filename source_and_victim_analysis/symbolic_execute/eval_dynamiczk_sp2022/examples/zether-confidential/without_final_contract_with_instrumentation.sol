pragma solidity ^0.8.2;

contract ZetherConfidential {
    uint32 MAX = 4294967295;
    uint EPOCH_SIZE = 1;
    uint total;
    mapping(address => uint) lastrollover;
    mapping(address => uint32) balance;
    mapping(address => uint32) pending;
    uint public priv_balance = 1;

    constructor() payable {
        address p0 = address(0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF);
        balance[p0] = 1000;
        pending[p0] = 0;
        lastrollover[p0] = 2;
        total = 1000;
    }

    function fund() public payable {
        rollover(msg.sender);
        require(total + msg.value <= MAX);
        priv_balance = priv_balance;
        balance[msg.sender] = balance[msg.sender] + uint32(msg.value);
        total = total + msg.value;
    }

    function transfer(address to, uint32 val) public {
        require(msg.sender != to);
        require(address(0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF) == to || address(0x6813Eb9362372EEF6200f3b1dbC3f819671cBA69) == to);
        rollover(msg.sender);
        rollover(to);
        require(val <= balance[msg.sender]);
        priv_balance = priv_balance * 0;
        balance[msg.sender] = balance[msg.sender] - val;
        pending[to] = pending[to] + val;
    }

    function burn(uint32 val) public {
        rollover(msg.sender);
        require(val <= balance[msg.sender]);
        priv_balance = priv_balance * 1;
        balance[msg.sender] = balance[msg.sender] - val;
        payable(msg.sender).transfer(val);
        total = total - val;
    }

    function rollover(address y) internal {
        uint e = block.number / EPOCH_SIZE;
        if (lastrollover[y] < e) {
            balance[y] = balance[y] + pending[y];
            pending[y] = 0;
            lastrollover[y] = e;
        }
    }
}