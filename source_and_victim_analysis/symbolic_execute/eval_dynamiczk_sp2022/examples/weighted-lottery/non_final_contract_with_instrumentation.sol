pragma solidity ^0.8.2;

contract WeightedLottery {
    address admin;
    uint bid_deadline;
    uint redeem_deadline;
    uint end_deadline;
    uint128 secret;
    uint32 jackpot;
    uint128 published_secret;
    uint32 published_jackpot;
    uint32 nof_winners;
    mapping(address => bool) is_winner;
    mapping(address => uint32) balance;
    mapping(address => uint128) bets_upper;
    mapping(address => uint128) bets_lower;
    uint _now = 1234;
    uint public priv_balance = 1;

    constructor() payable {
        address p2 = address(0x1efF47bc3a10a45D4B230B5d10E37751FE6AA718);
        address p1 = address(0x6813Eb9362372EEF6200f3b1dbC3f819671cBA69);
        address p0 = address(0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF);
        admin = p0;
        balance[p1] = 900;
        balance[p2] = 980;
        bid_deadline = 1236;
        redeem_deadline = 1238;
        end_deadline = 1241;
        secret = 193775903028374;
        nof_winners = 0;
        bets_lower[p1] = 193775903028370;
        bets_upper[p1] = 193775903028470;
        jackpot = 120;
        bets_lower[p2] = 20483;
        bets_upper[p2] = 20503;
    }

    function start(uint128 s) public {
        require(msg.sender == admin);
        require(_now > end_deadline);
        bid_deadline = _now + 2;
        redeem_deadline = _now + 4;
        end_deadline = _now + 7;
        secret = s;
        nof_winners = 0;
    }

    function buy() public payable {
        priv_balance = priv_balance;
        balance[msg.sender] = balance[msg.sender] + uint32(msg.value);
    }

    function sell(uint32 amount) public {
        require(amount <= balance[msg.sender]);
        priv_balance = 1 * priv_balance;
        balance[msg.sender] = balance[msg.sender] - amount;
        payable(msg.sender).transfer(amount);
    }

    function bet(uint128 lower, uint32 weight) public {
        require(_now <= bid_deadline);
        require(weight <= balance[msg.sender]);
        priv_balance = 0 * priv_balance;
        balance[msg.sender] = balance[msg.sender] - weight;
        bets_lower[msg.sender] = lower;
        bets_upper[msg.sender] = lower + weight;
        jackpot = jackpot + weight;
    }

    function add_winner(address winner) public {
        require(msg.sender != winner);
        require(address(0x1efF47bc3a10a45D4B230B5d10E37751FE6AA718) == winner || address(0x6813Eb9362372EEF6200f3b1dbC3f819671cBA69) == winner || address(0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF) == winner);
        require(msg.sender == admin);
        require(_now > bid_deadline);
        require(_now <= redeem_deadline);
        require((bets_lower[winner] <= secret) && (secret <= bets_upper[winner]));
        require(!is_winner[winner]);
        nof_winners = nof_winners + 1;
        is_winner[winner] = true;
    }

    function publish() public {
        require(msg.sender == admin);
        require(_now > bid_deadline);
        require(_now <= redeem_deadline);
        published_secret = secret;
        published_jackpot = jackpot;
    }

    function win() public {
        require(_now > redeem_deadline);
        require(_now <= end_deadline);
        require(is_winner[msg.sender]);
        priv_balance = 1 * priv_balance * 1;
        balance[msg.sender] = balance[msg.sender] + published_jackpot / nof_winners;
        is_winner[msg.sender] = false;
    }

    function _test_advance_time() public {
        _now = _now + 3;
    }
}