pragma solidity ^0.8.2;

contract ObliviousTransfer {
    address receiver;
    uint32 b1;
    uint32 b2;
    uint32 result;
    uint public priv_b1 = 1;
    uint public priv_result = 1;
    uint public priv_b2 = 1;

    constructor() payable {
        address p0 = address(0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF);
        receiver = p0;
        b1 = 0;
        b2 = 1;
        result = 59;
    }

    function prepare(uint32 s1, uint32 s2) public {
        require(msg.sender == receiver);
        require((s1 == 1 && s2 == 0) || (s1 == 0 && s2 == 1));
        priv_b1 = 0;
        b1 = s1;
        priv_b2 = 0;
        b2 = s2;
    }

    function send(uint32 x1, uint32 x2) public {
        priv_result = 0 * priv_b1 * 0 * priv_b2;
        result = b1 * x1 + b2 * x2;
    }
}