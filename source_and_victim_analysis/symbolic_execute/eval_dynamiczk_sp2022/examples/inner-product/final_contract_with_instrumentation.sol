pragma solidity ^0.8.2;

contract InnerProduct {
    address receiver;
    mapping(uint => uint32) vec;
    uint32 result;
    uint public priv_vec = 1;
    uint public priv_result = 1;

    constructor() payable {
        address p0 = address(0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF);
        receiver = p0;
        vec[0] = 2;
        vec[1] = 3;
    }

    function set_entry(uint idx, uint32 val) public {
        require(msg.sender == receiver);
        require(idx < 3);
        require(val <= 10);
        priv_vec = 0;
        vec[idx] = val;
    }

    function compute(uint32 x0, uint32 x1, uint32 x2) public {
        require(x0 <= 10);
        require(x1 <= 10);
        require(x2 <= 10);
        priv_result = 0 * priv_vec * 0 * 0;
        result = vec[0] * x0 + vec[1] * x1 + vec[2] * x2;
    }
}