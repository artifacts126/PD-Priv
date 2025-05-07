pragma solidity ^0.8.2;

contract Inheritance {
    uint DAY = 24 * 60 * 60;
    uint timeUntilAssumedDead = 120 * DAY;
    mapping(address => uint32) balance;
    mapping(address => uint32) total_inheritance_pledged;
    mapping(address => mapping(address => uint32)) inheritance_pledged_recv;
    mapping(address => mapping(address => uint32)) inheritance_pledged_send;
    mapping(address => uint) last_seen;
    uint _now = block.timestamp;
    uint public priv_inheritance_pledged_send = 1;
    uint public priv_total_inheritance_pledged = 1;
    uint public priv_balance = 1;

    constructor() payable {
        address p2 = address(0x1efF47bc3a10a45D4B230B5d10E37751FE6AA718);
        address p1 = address(0x6813Eb9362372EEF6200f3b1dbC3f819671cBA69);
        address p0 = address(0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF);
        balance[p0] = 70;
        last_seen[p0] = 1741789395;
        balance[p1] = 120;
        last_seen[p1] = 1741789395;
        balance[p2] = 100;
        last_seen[p2] = 1741789395;
        inheritance_pledged_send[p0][p1] = 50;
        inheritance_pledged_recv[p0][p1] = 50;
        total_inheritance_pledged[p0] = 70;
        inheritance_pledged_send[p0][p2] = 20;
        inheritance_pledged_recv[p0][p2] = 20;
    }

    function buy() public payable {
        priv_balance = priv_balance;
        balance[msg.sender] = balance[msg.sender] + uint32(msg.value);
        keep_alive();
    }

    function sell(uint32 v) public {
        require(balance[msg.sender] - total_inheritance_pledged[msg.sender] >= v);
        priv_balance = priv_balance * 1;
        balance[msg.sender] = balance[msg.sender] - v;
        payable(msg.sender).transfer(v);
        keep_alive();
    }

    function transfer(uint32 v, address receiver) public {
        require(msg.sender != receiver);
        require(address(0x1efF47bc3a10a45D4B230B5d10E37751FE6AA718) == receiver || address(0x6813Eb9362372EEF6200f3b1dbC3f819671cBA69) == receiver || address(0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF) == receiver);
        require(balance[msg.sender] - total_inheritance_pledged[msg.sender] >= v);
        priv_balance = priv_balance * 0;
        balance[msg.sender] = balance[msg.sender] - v;
        balance[receiver] = balance[receiver] + v;
        keep_alive();
    }

    function pledge_inheritance(address recipient, uint32 amount) public {
        require(msg.sender != recipient);
        require(address(0x1efF47bc3a10a45D4B230B5d10E37751FE6AA718) == recipient || address(0x6813Eb9362372EEF6200f3b1dbC3f819671cBA69) == recipient || address(0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF) == recipient);
        uint32 old_amount = inheritance_pledged_send[msg.sender][recipient];
        require(balance[msg.sender] - total_inheritance_pledged[msg.sender] + old_amount >= amount);
        priv_inheritance_pledged_send = 0;
        inheritance_pledged_send[msg.sender][recipient] = amount;
        inheritance_pledged_recv[msg.sender][recipient] = amount;
        priv_total_inheritance_pledged = priv_total_inheritance_pledged * 0 * 1;
        total_inheritance_pledged[msg.sender] = total_inheritance_pledged[msg.sender] + amount - old_amount;
        keep_alive();
    }

    function claim_inheritance(address sender) public {
        require(msg.sender != sender);
        require(address(0x1efF47bc3a10a45D4B230B5d10E37751FE6AA718) == sender || address(0x6813Eb9362372EEF6200f3b1dbC3f819671cBA69) == sender || address(0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF) == sender);
        require(_now - last_seen[sender] >= timeUntilAssumedDead);
        uint32 amount = inheritance_pledged_recv[sender][msg.sender];
        priv_balance = 1 * priv_balance;
        balance[msg.sender] = balance[msg.sender] + amount;
        balance[sender] = balance[sender] - amount;
        total_inheritance_pledged[sender] = total_inheritance_pledged[sender] - amount;
        inheritance_pledged_recv[sender][msg.sender] = 0;
        priv_inheritance_pledged_send = 1;
        inheritance_pledged_send[sender][msg.sender] = 0;
        keep_alive();
    }

    function keep_alive() public {
        last_seen[msg.sender] = _now;
    }

    function _test_advance_time() public {
        _now = _now + timeUntilAssumedDead;
    }
}