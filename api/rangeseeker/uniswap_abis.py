from eth_typing import ABI

UNISWAP_V3_POSITION_MANAGER_POSITIONS_ABI: ABI = [
    {
        'inputs': [{'name': 'tokenId', 'type': 'uint256'}],
        'name': 'positions',
        'outputs': [
            {'name': 'nonce', 'type': 'uint96'},
            {'name': 'operator', 'type': 'address'},
            {'name': 'token0', 'type': 'address'},
            {'name': 'token1', 'type': 'address'},
            {'name': 'fee', 'type': 'uint24'},
            {'name': 'tickLower', 'type': 'int24'},
            {'name': 'tickUpper', 'type': 'int24'},
            {'name': 'liquidity', 'type': 'uint128'},
            {'name': 'feeGrowthInside0LastX128', 'type': 'uint256'},
            {'name': 'feeGrowthInside1LastX128', 'type': 'uint256'},
            {'name': 'tokensOwed0', 'type': 'uint128'},
            {'name': 'tokensOwed1', 'type': 'uint128'},
        ],
        'stateMutability': 'view',
        'type': 'function',
    }
]
