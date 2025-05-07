pragma solidity ^0.8.2;

contract Odd_Even {
    address admin;
    uint32 sum;
    uint counter = 0;
    mapping(address => uint32) balance;
    mapping(uint => address) players;
    address winner;
    uint play_deadline;
    uint _now = block.timestamp;
    uint public priv_sum = 1;
    uint public priv_balance = 1;

    constructor() payable {
        address p0 = address(0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF);
        address p1 = address(0x6813Eb9362372EEF6200f3b1dbC3f819671cBA69);
        address p2 = address(0x1efF47bc3a10a45D4B230B5d10E37751FE6AA718);
        admin = p0;
        balance[p0] = 1000;
        balance[p1] = 1000;
        balance[p2] = 999;
        sum = 21;
        play_deadline = 1741616703;
        players[0] = p1;
        counter = 1;
        players[1] = p2;
        _now = 1741616704;
        winner = p1;
    }

    function buy() public payable {
        priv_balance = priv_balance;
        balance[msg.sender] = balance[msg.sender] + uint32(msg.value);
    }

    function transfer(uint32 amount, address to) public {
        require(msg.sender != to);
        require(address(0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF) == to || address(0x6813Eb9362372EEF6200f3b1dbC3f819671cBA69) == to || address(0x1efF47bc3a10a45D4B230B5d10E37751FE6AA718) == to);
        require(amount <= balance[msg.sender]);
        priv_balance = priv_balance * 0;
        balance[msg.sender] = balance[msg.sender] - amount;
        balance[to] = balance[to] + amount;
    }

    function sell(uint32 amount) public {
        require(amount <= balance[msg.sender]);
        priv_balance = priv_balance * 1;
        balance[msg.sender] = balance[msg.sender] - amount;
        payable(msg.sender).transfer(amount);
    }

    function start(uint32 number) public {
        require(msg.sender == admin);
        require(_now > play_deadline);
        if (counter >= 1) {
            address player1 = players[0];
            balance[player1] = balance[player1] + 1;
            if (counter == 2) {
                address player2 = players[1];
                balance[player2] = balance[player2] + 1;
            }
            counter = 0;
        }
        priv_sum = priv_sum * 0;
        sum = sum + number;
        play_deadline = _now + 2;
    }

    function play(uint32 number) public {
        require(_now <= play_deadline);
        require(1 <= balance[msg.sender]);
        require(counter < 2);
        require(msg.sender != admin);
        priv_balance = priv_balance;
        balance[msg.sender] = balance[msg.sender] - 1;
        priv_sum = priv_sum * 0;
        sum = sum + number;
        players[counter] = msg.sender;
        counter = counter + 1;
    }

    function select_winner() public {
        require(msg.sender == admin);
        require(_now > play_deadline);
        if (counter == 1) {
            address player = players[0];
            balance[player] = balance[player] + 1;
        }
        if (counter == 2) {
            uint index = sum % 2;
            winner = players[index];
            balance[winner] = balance[winner] + 2;
        }
        counter = 0;
    }

    function _test_advance_time() public {
        _now = _now + 3;
    }
}