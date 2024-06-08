from web3 import Web3
    
WBTC_adr = Web3.to_checksum_address("0x1bfd67037b42cf73acf2047067bd4f2c47d9bfd6") 
WETH_adr = Web3.to_checksum_address("0x7ceb23fd6bc0add59e62ac25578270cff1b9f619") 
USDT_adr = Web3.to_checksum_address("0xc2132d05d31c914a87c6611c10748aeb04b58e8f")
UniswapV3Factory = Web3.to_checksum_address("0x1F98431c8aD98523631AE4a59f267346ea31F984")
SwapRouter = Web3.to_checksum_address('0xE592427A0AEce92De3Edee1F18E0157C05861564')
Wallet = Web3.to_checksum_address('...') 
Private_key = '...'

adr_dict = {
    'USDT' : USDT_adr,
    'WETH' : WETH_adr,
    'WBTC' : WBTC_adr,
    'Factory' : UniswapV3Factory,
    'Router' : SwapRouter,
    'Wallet' : Wallet,
    'Key' : Private_key
}

