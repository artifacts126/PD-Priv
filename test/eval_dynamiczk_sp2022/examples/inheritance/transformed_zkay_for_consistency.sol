pragma zkay ^0.3.0;

contract Inheritance {
    final uint DAY = 24 * 60 * 60;
    final uint timeUntilAssumedDead = 120 * DAY;
    mapping(address => uint32) balance_original;
    mapping(address => uint32) total_inheritance_pledged_original;
    mapping(address => mapping(address => uint32)) inheritance_pledged_recv_original;
    mapping(address => mapping(address => uint32)) inheritance_pledged_send_original;
    mapping(address => uint) last_seen;
    uint _now = block.timestamp;
    mapping(address!x => uint32@x<+>) balance;
    mapping(address!x => uint32@x<+>) total_inheritance_pledged;
    mapping(address => mapping(address!x => uint32@x)) inheritance_pledged_recv;
    mapping(address!x => mapping(address => uint32@x)) inheritance_pledged_send;

    constructor(bool  migrate__now, uint  value__now) public {
        if (migrate__now) {
            _now = value__now;
        }
    }

    function buy() public payable {
        balance[me] = addhom(unhom(balance[me]) + reveal(uint32(msg.value), me));
        keep_alive();
    }

    function sell(uint32 v) public {
        require(reveal(unhom(balance[me]) - unhom(total_inheritance_pledged[me]) >= reveal(v, me), all));
        balance[me] = addhom(unhom(balance[me]) - reveal(v, me));
        msg.sender.transfer(v);
        keep_alive();
    }

    function transfer(uint32@me v, address receiver) public {
        require(reveal(unhom(balance[me]) - unhom(total_inheritance_pledged[me]) >= v, all));
        balance[me] = addhom(unhom(balance[me]) - v);
        balance[receiver] = balance[receiver] + reveal(v, receiver);
        keep_alive();
    }

    function pledge_inheritance(address recipient, uint32@me amount) public {
        uint32@me old_amount = inheritance_pledged_send[me][recipient];
        require(reveal(unhom(balance[me]) - unhom(total_inheritance_pledged[me]) + old_amount >= amount, all));
        inheritance_pledged_send[me][recipient] = amount;
        inheritance_pledged_recv[me][recipient] = reveal(amount, recipient);
        total_inheritance_pledged[me] = addhom(unhom(total_inheritance_pledged[me]) + amount - old_amount);
        keep_alive();
    }

    function claim_inheritance(address sender) public {
        require(_now - last_seen[sender] >= timeUntilAssumedDead);
        uint32@me amount = inheritance_pledged_recv[sender][me];
        balance[me] = addhom(unhom(balance[me]) + amount);
        balance[sender] = balance[sender] - reveal(amount, sender);
        total_inheritance_pledged[sender] = total_inheritance_pledged[sender] - reveal(amount, sender);
        inheritance_pledged_recv[sender][me] = reveal(0, me);
        inheritance_pledged_send[sender][me] = reveal(0, sender);
        keep_alive();
    }

    function keep_alive() public {
        last_seen[me] = _now;
    }

    function _test_advance_time() public {
        _now = _now + timeUntilAssumedDead;
    }

    function consistency_balance(address param1) public {
        balance[param1] = reveal(balance_original[param1], param1);
    }

    function consistency_total_inheritance_pledged(address param1) public {
        total_inheritance_pledged[param1] = reveal(total_inheritance_pledged_original[param1], param1);
    }

    function consistency_inheritance_pledged_recv(address param1, address param2) public {
        inheritance_pledged_recv[param1][param2] = reveal(inheritance_pledged_recv_original[param1][param2], param2);
    }

    function consistency_inheritance_pledged_send(address param1, address param2) public {
        inheritance_pledged_send[param1][param2] = reveal(inheritance_pledged_send_original[param1][param2], param1);
    }

    function migration_balance_original(address[] calldata key1_balance_original, uint32[] calldata value_balance_original) external {
        require(key1_balance_original.length == value_balance_original.length);
        uint i;
        for (i = 0; i < value_balance_original.length; i = i + 1) {
            balance_original[key1_balance_original[i]] = value_balance_original[i];
        }
    }

    function migration_total_inheritance_pledged_original(address[] calldata key1_total_inheritance_pledged_original, uint32[] calldata value_total_inheritance_pledged_original) external {
        require(key1_total_inheritance_pledged_original.length == value_total_inheritance_pledged_original.length);
        uint i;
        for (i = 0; i < value_total_inheritance_pledged_original.length; i = i + 1) {
            total_inheritance_pledged_original[key1_total_inheritance_pledged_original[i]] = value_total_inheritance_pledged_original[i];
        }
    }

    function migration_inheritance_pledged_recv_original(address[] calldata key1_inheritance_pledged_recv_original, address[] calldata key2_inheritance_pledged_recv_original, uint32[] calldata value_inheritance_pledged_recv_original) external {
        require(key1_inheritance_pledged_recv_original.length == value_inheritance_pledged_recv_original.length);
        require(key2_inheritance_pledged_recv_original.length == value_inheritance_pledged_recv_original.length);
        uint i;
        for (i = 0; i < value_inheritance_pledged_recv_original.length; i = i + 1) {
            inheritance_pledged_recv_original[key1_inheritance_pledged_recv_original[i]][key2_inheritance_pledged_recv_original[i]] = value_inheritance_pledged_recv_original[i];
        }
    }

    function migration_inheritance_pledged_send_original(address[] calldata key1_inheritance_pledged_send_original, address[] calldata key2_inheritance_pledged_send_original, uint32[] calldata value_inheritance_pledged_send_original) external {
        require(key1_inheritance_pledged_send_original.length == value_inheritance_pledged_send_original.length);
        require(key2_inheritance_pledged_send_original.length == value_inheritance_pledged_send_original.length);
        uint i;
        for (i = 0; i < value_inheritance_pledged_send_original.length; i = i + 1) {
            inheritance_pledged_send_original[key1_inheritance_pledged_send_original[i]][key2_inheritance_pledged_send_original[i]] = value_inheritance_pledged_send_original[i];
        }
    }

    function migration_last_seen(address[] calldata key1_last_seen, uint[] calldata value_last_seen) external {
        require(key1_last_seen.length == value_last_seen.length);
        uint i;
        for (i = 0; i < value_last_seen.length; i = i + 1) {
            last_seen[key1_last_seen[i]] = value_last_seen[i];
        }
    }
}