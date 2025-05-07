pragma solidity ^0.8.2;

contract IndexFunds {
    address admin;
    mapping(address => uint32) stocks_in_funds;
    mapping(address => uint32) stock_price;
    uint32 current_funds_price;
    mapping(address => uint32) balance;
    mapping(address => uint32) shares;
    uint32 total_shares;
    uint public priv_shares = 1;
    uint public priv_balance = 1;

    constructor() payable {
        address p2 = address(0x1efF47bc3a10a45D4B230B5d10E37751FE6AA718);
        address p3 = address(0xe1AB8145F7E55DC933d51a18c793F901A3A0b276);
        address p0 = address(0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF);
        address p1 = address(0x6813Eb9362372EEF6200f3b1dbC3f819671cBA69);
        admin = p0;
        stocks_in_funds[p2] = 1;
        stock_price[p2] = 10;
        current_funds_price = 25;
        stocks_in_funds[p3] = 3;
        stock_price[p3] = 5;
        balance[p1] = 0;
        total_shares = 10;
        shares[p1] = 10;
    }

    function add_stocks_to_funds(address stock, uint32 amount, uint32 initial_price) public {
        require(msg.sender != stock);
        require(address(0x1efF47bc3a10a45D4B230B5d10E37751FE6AA718) == stock || address(0xe1AB8145F7E55DC933d51a18c793F901A3A0b276) == stock || address(0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF) == stock || address(0x6813Eb9362372EEF6200f3b1dbC3f819671cBA69) == stock);
        require(msg.sender == admin);
        require(stocks_in_funds[stock] == 0);
        stocks_in_funds[stock] = amount;
        stock_price[stock] = initial_price;
        current_funds_price = current_funds_price + amount * initial_price;
    }

    function pay_into() public payable {
        priv_balance = priv_balance;
        balance[msg.sender] = balance[msg.sender] + uint32(msg.value);
    }

    function pay_out(uint32 val) public {
        require(balance[msg.sender] >= val);
        priv_balance = priv_balance * 1;
        balance[msg.sender] = balance[msg.sender] - val;
        payable(msg.sender).transfer(val);
    }

    function buy_shares(uint32 num_shares) public {
        require(balance[msg.sender] >= num_shares * current_funds_price);
        total_shares = total_shares + num_shares;
        priv_shares = 0 * priv_shares;
        shares[msg.sender] = shares[msg.sender] + num_shares;
        priv_balance = 1 * 0 * priv_balance;
        balance[msg.sender] = balance[msg.sender] - num_shares * current_funds_price;
    }

    function sell_shares(uint32 num_shares) public {
        require(shares[msg.sender] >= num_shares);
        total_shares = total_shares - num_shares;
        priv_shares = 0 * priv_shares;
        shares[msg.sender] = shares[msg.sender] - num_shares;
        priv_balance = 1 * 0 * priv_balance;
        balance[msg.sender] = balance[msg.sender] + num_shares * current_funds_price;
    }

    function report_new_stock_price(uint32 new_price) public payable {
        require(stocks_in_funds[msg.sender] > 0);
        uint32 old_price = stock_price[msg.sender];
        stock_price[msg.sender] = new_price;
        current_funds_price = current_funds_price - old_price * stocks_in_funds[msg.sender] + new_price * stocks_in_funds[msg.sender];
    }
}