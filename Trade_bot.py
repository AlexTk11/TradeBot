from web3 import Web3
import json
from BotTools import adr_dict
import time
import math
import asyncio

# WETH/USDT 
# Infura -> Polygon -> Uniswap

class token:
    def __init__(self, Token_adress, decimals, token_contract) -> None:
        self.adr = Token_adress
        self.dec = decimals
        self.contract = token_contract
        

class TradeBot:
    def __init__(self, fee = 3000) -> None:
        self.gas_const = 1.3 #коэфициент цены на газ
        self.UV3Factory_adr = adr_dict['Factory'] 
        self.UV3SwapRouter_adr = adr_dict['Router']
        self.wallet = adr_dict['Wallet']
        self.private_key = adr_dict['Key']
        self.w3 = Web3(Web3.HTTPProvider('https://polygon-mainnet.infura.io/v3/c89171f02c6a451a9644d419a387852f')) #!!!
        self.fee = fee
        self.pool_abi = json.load(open("PoolABI.json", 'r'))
        self.uniswap_factory_abi = json.load(open("FactoryABI.json", 'r'))
        self.swap_abi = json.load(open("SwapABI.json", 'r'))
        self.token_abi = json.load(open("ERC-20_ABI.json", 'r'))
        
        self.tokenUSDT = token(
            adr_dict['USDT'], #Адрес USDT
            6, #Decimalsd USDT
            self.w3.eth.contract(address=adr_dict['USDT'], abi=self.token_abi)
        ) #USDT token contract 
        self.tokenWETH = token(
            adr_dict['WETH'], #Адрес WETH
            18, #Decimalsd WETH
            self.w3.eth.contract(address=adr_dict['WETH'], abi=self.token_abi)
        ) #WETH token contract 
        
        

        factory_contract = self.w3.eth.contract(address=self.UV3Factory_adr, abi=self.uniswap_factory_abi) 
        self.poolAdr = factory_contract.functions.getPool(self.tokenUSDT.adr, self.tokenWETH.adr, self.fee).call() #Получение адреса пула для установленной комиссии и токенов.
        self.pool_contract = self.w3.eth.contract(address=self.poolAdr, abi=self.pool_abi) 

        self.chainID = self.w3.eth.chain_id
        return
    

    def getCurrentTickPrice(self): #возвращает цену weth/usdt
        slot0_res = self.pool_contract.functions.slot0().call() #вызов метода slot0() контракта UniswapV3Pool
        tick = slot0_res[1]
        tick_price = 1.0001 ** tick * (10 ** (self.tokenWETH.dec - self.tokenUSDT.dec))#перевод значения цены тика в адекватный вид
        return tick_price
        

    
                

    async def approve(self, token, amount = 2 ** 256 - 1):#Подтверждение расхода токенов
        nonce = self.w3.eth.get_transaction_count(self.wallet) #порядковый номер транзакции, отправляемой с данного кошелька
        token_contract = token.contract
        tx = token_contract.functions.approve(
            self.UV3SwapRouter_adr, #адрес контракта 
            amount #сумма одобренного расхода
            ).build_transaction({
            'from': self.wallet, #кошелек
            'nonce': nonce, 
            "gasPrice": int(self.w3.eth.gas_price * self.gas_const), #расчет цены за газ
            'gas' : 10000000, #количество газа, непотраченный газ не расходуется 
            "chainId": self.chainID # ID сети, для Polygon 137
            })

        signed_tx = self.w3.eth.account.sign_transaction(tx, self.private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        return tx_hash.hex()#, tx_hash.hex()

    async def swap(self, amount, mode = 0): #mode == 0 : USDT -> WETH; mode != 0 : WETH -> USDT
        if mode == 0:
            token_in = self.tokenUSDT
            token_out = self.tokenWETH  
        else:
            token_in = self.tokenWETH
            token_out = self.tokenUSDT
        
        amount_in = int((amount) * (10 ** token_in.dec)) - 1
      
    
        swap_contract = self.w3.eth.contract(address=self.UV3SwapRouter_adr, abi=self.swap_abi)
        
        if mode == 0:
            amountMin, priceLimit = self.makeAmountLimitUsdt(amount_in, self.getPriceX96(), slippage=5)
        else:
            amountMin, priceLimit = self.makeAmountLimitWeth(amount_in, self.getPriceX96(), slippage=5) #Устанавливаем проскальзывание цены при обмене в 5%
            #print(amountMin, priceLimit)
        deadline = int(time.time()) + 600 #Дедлайн выполнения транзакции swaprouter - 10 мин
        
        nonce = self.w3.eth.get_transaction_count(self.wallet)
        tx_hash = swap_contract.functions.exactInputSingle({
                'tokenIn': token_in.adr, 
                'tokenOut': token_out.adr, 
                'fee': self.fee,  #fee
                'recipient': self.wallet,
                'deadline': deadline,
                'amountIn': amount_in,
                'amountOutMinimum': amountMin,
                'sqrtPriceLimitX96': priceLimit,
        }).build_transaction({
            'from': self.wallet,
            'nonce': nonce,  
            'gas': 10000000,              
            'gasPrice': int(self.w3.eth.gas_price *  self.gas_const), 
            'chainId': self.chainID
        })
        signed_txn = self.w3.eth.account.sign_transaction(tx_hash, self.private_key) #Подписываем транзакцию
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)#отправляем транзакцию
        print("Swap transaction successful!")
        return tx_hash.hex()

    def makeInput(self, dim = 5, time_delay = 1800, price_time  = 60): #time_delay - шаг между значениями цены; price_time - время, по которому усредняется цена
        
        time_tmp = list(range((dim - 1) * time_delay, -1, -time_delay))
        timestamps = []
        for i in time_tmp:
            timestamps.append(i + price_time)
            timestamps.append(i)
        
        obs_res = self.pool_contract.functions.observe(timestamps).call()
        comulatives = obs_res[0]
        #print(comulatives, timestamps)
        res = []
        for i in range(dim * 2 - 1, -1, -2):
            res.append(1.0001 ** ((comulatives[i] - comulatives[i - 1]) / (price_time)))
        return res
    
    def convertToX96(self, price):#переводит цену в формат sqrtX96
        return int((math.sqrt(price)) * 2 ** 96)

    def convertFromX96(self, price):
        price = (price/(2 ** 96)) ** 2
        return price

    def getPriceX96(self):
        slot0_res = self.pool_contract.functions.slot0().call() #вызов метода slot0() контракта UniswapV3Pool
        return slot0_res[0]

    def makeAmountLimitWeth(self,  amount, priceSqrtX96, slippage = 5): #slippage - процент проскальзывания цены для текущей сделки;
        price = self.convertFromX96(priceSqrtX96)
        lower_price = price * (1 - slippage/100)
        return (int(amount * lower_price) - 1), (int(self.convertToX96(lower_price)) - 1)
     
    def makeAmountLimitUsdt(self,  amount, priceSqrtX96, slippage = 5): #slippage - процент проскальзывания цены для текущей сделки;
        price = 1 / self.convertFromX96(priceSqrtX96)
        lower_price = price * (1 - slippage/100)
        return (int(amount * lower_price) - 1), (int(self.convertToX96(lower_price)) - 1)

    def getPriceByObs(self, time_delay): #Возвращает средневзвешенную цену wei/USDT*10^-6 за последние time_delay секунд
        obs_res = self.pool_contract.functions.observe([time_delay, 0]).call()
        comulatives = obs_res[0]
        tick_price = (comulatives[1] - comulatives[0]) / time_delay
        return 1.0001 ** tick_price
        

    def getStatus(self, tx_hash):
        txn = self.w3.eth.get_transaction_receipt(tx_hash)
        return txn['status']

    def getTokenUSDT(self):
        return self.tokenUSDT

    def getTokenWeth(self):
        return self.tokenWETH

    def getGas(self):
        return self.w3.eth.gas_price

    def getAllowance(self, token):
        allowance = token.contract.functions.allowance(
            self.wallet, self.UV3SwapRouter_adr).call()
        return allowance




        
   


