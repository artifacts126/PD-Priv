pragma solidity ^0.8.2;

contract ZetherLarge {
    uint EPOCH_SIZE = 1;
    mapping(address => uint) lastrollover;
    mapping(address => uint32) balance;
    mapping(address => uint32) pending;
    mapping(address => uint128) vault;
    uint public priv_balance = 1;
    uint public priv_vault = 1;

    constructor() payable {
        address p1 = address(0x6813Eb9362372EEF6200f3b1dbC3f819671cBA69);
        address p0 = address(0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF);
        balance[p0] = 900;
        pending[p0] = 0;
        lastrollover[p0] = 3;
        balance[p1] = 55;
        pending[p1] = 0;
        lastrollover[p1] = 4;
        vault[p1] = 45;
    }

    function fund() public payable {
        rollover(msg.sender);
        priv_balance = priv_balance;
        balance[msg.sender] = balance[msg.sender] + uint32(msg.value);
    }

    function transfer(address to, uint32 val) public {
        require(msg.sender != to);
        require(address(0x6813Eb9362372EEF6200f3b1dbC3f819671cBA69) == to || address(0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF) == to);
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
    }

    function into_vault(uint32 val) public {
        rollover(msg.sender);
        require(val <= balance[msg.sender]);
        priv_vault = priv_vault;
        vault[msg.sender] = vault[msg.sender] + val;
        priv_balance = priv_balance * 0;
        balance[msg.sender] = balance[msg.sender] - val;
    }

    function from_vault(uint32 val) public {
        require(val <= vault[msg.sender]);
        priv_vault = priv_vault;
        vault[msg.sender] = vault[msg.sender] - val;
        priv_balance = priv_balance * 0;
        balance[msg.sender] = balance[msg.sender] + val;
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