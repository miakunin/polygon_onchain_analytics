import requests
from web3 import Web3
from datetime import datetime, timedelta
import time
from pycoingecko import CoinGeckoAPI

# Ваш API ключ
API_KEY = "ZI1T41EWX4AD33XWRVJW7HGJRSZ5F9IZPW"

# Альтернативные RPC-эндпоинты для Polygon
RPC_OPTIONS = [
    f"https://polygon-mainnet.g.alchemy.com/v2/{API_KEY}",
    f"https://polygon-rpc.com",
    f"https://rpc-mainnet.matic.network",
    f"https://matic-mainnet.chainstacklabs.com"
]

# API для Polygonscan
POLYGONSCAN_API = "https://api.polygonscan.com/api"

# Установка адреса кошелька
WALLET_ADDRESS = "0xA21bC476F61Ae15698EB659b30c5Ed996E51D532"
WALLET_ADDRESS = "0xcc922a4e2e526114fcf9d7205d7a805b8c4263e9"
WALLET_ADDRESS = "0x64dAED14a114B0281F0216412412973A3Af360C7"
WALLET_ADDRESS = "0x47182d25d7fb7D96aA754c4e88c2f9a35d2a65c4"

# Инициализация CoinGecko API
cg = CoinGeckoAPI()

def ensure_checksum_address(address):
    """
    Convert a lowercase or mixed-case address to a checksum address
    
    Args:
        address (str): Ethereum/Polygon wallet address
    
    Returns:
        str: Checksum-formatted address
    """
    try:
        return Web3.to_checksum_address(address)
    except Exception as e:
        print(f"Error converting address {address}: {e}")
        return address


# Функция для попытки подключения к разным RPC-эндпоинтам
def get_web3_connection():
    for rpc_url in RPC_OPTIONS:
        try:
            web3 = Web3(Web3.HTTPProvider(rpc_url))
            if web3.is_connected():
                global WALLET_ADDRESS
                WALLET_ADDRESS = web3.to_checksum_address(WALLET_ADDRESS)
                print(f"Успешно подключено к: {rpc_url}")
                return web3
        except Exception as e:
            print(f"Не удалось подключиться к {rpc_url}: {e}")
    
    print("Не удалось подключиться ни к одному RPC-эндпоинту. Используем API Polygonscan.")
    return None


def get_wallet_creation_date(address):
    """Получение даты первой транзакции (приближенная дата создания кошелька)"""
    params1 = {
        "module": "account",
        "action": "txlist",
        "address": address,
        "startblock": 0,
        "endblock": 99999999,
        "page": 1,
        "offset": 1,
        "sort": "asc",
        "apikey": API_KEY
    }
        
    params2 = {
        "module": "account",
        "action": "tokentx",
        "address": address,
        "startblock": 0,
        "endblock": 99999999,
        "page": 1,
        "offset": 1,
        "sort": "asc",
        "apikey": API_KEY
    }

    try:
        response_tx = requests.get(POLYGONSCAN_API, params=params1)
        data_tx = response_tx.json()
        response_tokens = requests.get(POLYGONSCAN_API, params=params2)
        data_tokens = response_tokens.json()        

        if data_tx["status"] == "1" and len(data_tx["result"]) > 0:
            first_tx = data_tx["result"][0]
            timestamp = int(first_tx["timeStamp"])
            creation_date_tx = datetime.fromtimestamp(timestamp)

        if data_tokens["status"] == "1" and len(data_tokens["result"]) > 0:
            first_tokens = data_tokens["result"][0]
            timestamp = int(first_tokens["timeStamp"])
            creation_date_tokens = datetime.fromtimestamp(timestamp)
            try:
                creation_date_tx
            except NameError:
                return creation_date_tokens
            else:
                if creation_date_tokens < creation_date_tx:
                    return creation_date_tokens
                else:
                    return creation_date_tx
        else:
            error_msg = data_tokens.get("message", "Неизвестная ошибка")
            print(f"Ошибка API Polygonscan: {error_msg}")
            return "Информация о первой транзакции не найдена"
    except Exception as e:
        print(f"Ошибка при запросе к Polygonscan API: {e}")
        return "Ошибка при получении данных"

def get_wallet_balance(address, web3_instance):
    """
    Get wallet balance in native currency (MATIC)
    
    Args:
        address (str): Wallet address
        web3_instance (Web3): Web3 connection instance
    
    Returns:
        dict: Balance information
    """
    try:
        # Ensure checksum address
        address = ensure_checksum_address(address)
        
        # Get balance in MATIC
        balance_wei = web3_instance.eth.get_balance(address)
        balance_matic = web3_instance.from_wei(balance_wei, 'ether')
        
        # Get current MATIC price in USD
        matic_price = get_token_price_in_usd("0x0000000000000000000000000000000000000000")
        balance_usd = float(balance_matic) * matic_price
        
        return {
            "balance_matic": round(float(balance_matic), 4),
            "balance_usd": round(balance_usd, 2)
        }
    except Exception as e:
        print(f"Error getting MATIC balance for {address}: {e}")
        return {
            "balance_matic": 0,
            "balance_usd": 0
        }


def get_transactions_last_month(address):
    """Получение обычных транзакций за последний месяц"""
    # Расчет временного интервала (30 дней)
    end_timestamp = int(time.time())
    start_timestamp = int((datetime.now() - timedelta(days=30)).timestamp())
    
    params = {
        "module": "account",
        "action": "txlist",
        "address": address,
        "startblock": 0,
        "endblock": 99999999,
        "page": 1,
        "offset": 10000,  # Большое значение, чтобы получить все транзакции
        "sort": "desc",
        "apikey": API_KEY
    }
    
    try:
        response = requests.get(POLYGONSCAN_API, params=params)
        data = response.json()
        
        if data["status"] == "1":
            # Фильтрация транзакций вручную по timestamp
            filtered_txs = [
                tx for tx in data["result"] 
                if start_timestamp <= int(tx["timeStamp"]) <= end_timestamp
            ]
            return filtered_txs
        else:
            error_msg = data.get("message", "Неизвестная ошибка")
            print(f"Ошибка API Polygonscan: {error_msg}")
            return []
    except Exception as e:
        print(f"Ошибка при запросе к Polygonscan API: {e}")
        return []

def get_erc20_transactions_last_month(address):
    """Получение ERC-20 транзакций за последний месяц"""
    # Расчет временного интервала (30 дней)
    end_timestamp = int(time.time())
    start_timestamp = int((datetime.now() - timedelta(days=30)).timestamp())
    
    params = {
        "module": "account",
        "action": "tokentx",
        "address": address,
        "startblock": 0,
        "endblock": 99999999,
        "page": 1,
        "offset": 10000,  # Большое значение, чтобы получить все транзакции
        "sort": "desc",
        "apikey": API_KEY
    }
    
    try:
        response = requests.get(POLYGONSCAN_API, params=params)
        data = response.json()
        
        if data["status"] == "1":
            # Фильтрация транзакций вручную по timestamp
            filtered_txs = [
                tx for tx in data["result"] 
                if start_timestamp <= int(tx["timeStamp"]) <= end_timestamp
            ]
            return filtered_txs
        else:
            error_msg = data.get("message", "Неизвестная ошибка")
            print(f"Ошибка API Polygonscan: {error_msg}")
            return []
    except Exception as e:
        print(f"Ошибка при запросе к Polygonscan API: {e}")
        return []

def get_token_price_in_usd(token_address):
    """
    Получение текущей цены токена в USD через CoinGecko.
    Для анализа транзакций за последний месяц текущая цена является достаточно точной.
    """
    token_address_normalized = token_address.lower().strip()
    
    # Словарь с маппингом адресов на ID в CoinGecko
    token_info = {
        "0x2791bca1f2de4661ed88a30c99a7a9449aa84174": "usd-coin",  # USDCe
        "0x8f3cf7ad23cd3cadbd9735aff958023239c6a063": "dai",       # DAI
        "0xc2132d05d31c914a87c6611c10748aeb04b58e8f": "tether",    # USDT
        "0x3c499c542cef5e3811e1192ce70d8cc03d5c3359": "usdc",      # Circle: USDC Token
        "0x0000000000000000000000000000000000000000": "matic-network"  # Native MATIC
    }
    
    # Стейблкоины всегда оцениваются в 1 USD
    stablecoins = ["usd-coin", "dai", "tether", "usdc"]
    
    try:
        # Проверка API CoinGecko
        if 'cg' not in globals():
            from pycoingecko import CoinGeckoAPI
            global cg
            cg = CoinGeckoAPI()
        
        # Для стейблкоинов сразу возвращаем 1 USD
        token_id = token_info.get(token_address_normalized)
        if token_id in stablecoins:
            return 1.0
        
        # Если токен найден в словаре
        if token_id:
            try:
                price_data = cg.get_price(ids=token_id, vs_currencies='usd')
                if price_data and token_id in price_data:
                    return price_data[token_id]['usd']
                else:
                    print(f"Нет данных о цене для {token_id}")
                    return 0
            except Exception as e:
                print(f"Ошибка API при получении цены для {token_id}: {e}")
                # Для MATIC используем запасное значение при ошибке API
                if token_id == "matic-network":
                    return 0.7  # Примерная цена MATIC
                return 0
        
        # Проверка на стейблкоины по названию
        if any(stable_term in token_address_normalized for stable_term in ["usdc", "usdt", "dai", "usd"]):
            return 1.0
            
        # Если токен не распознан
        print(f"Не удалось определить цену токена {token_address_normalized}")
        return 0
            
    except Exception as e:
        print(f"Критическая ошибка при получении цены токена: {e}")
        return 0

def calculate_transaction_value_in_usd(transaction, is_erc20=False, web3_instance=None):
    """Расчет стоимости транзакции в USD по текущим ценам"""
    try:
        if is_erc20:
            # Для ERC-20 токенов
            token_address = transaction["contractAddress"]
            value = int(transaction["value"]) / (10 ** int(transaction["tokenDecimal"]))
            token_price = get_token_price_in_usd(token_address)
            return value * token_price
        else:
            # Для нативных MATIC транзакций
            if web3_instance:
                value = web3_instance.from_wei(int(transaction["value"]), 'ether')
            else:
                value = int(transaction["value"]) / 1e18  # Преобразование из wei в MATIC
            matic_price = get_token_price_in_usd("0x0000000000000000000000000000000000000000")
            return float(value) * matic_price
    except Exception as e:
        print(f"Ошибка при расчете стоимости: {e}")
        return 0

def generate_wallet_summary(address, web3_instance=None):
    """Генерация полной сводки по кошельку за последние 30 дней"""
    # Дата создания (первая транзакция)
    creation_date = get_wallet_creation_date(address)
    
    # Даты анализируемого периода
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    # Получение транзакций за последний месяц
    regular_txs = get_transactions_last_month(address)
    erc20_txs = get_erc20_transactions_last_month(address)

    # Общее количество транзакций
    total_tx_count = len(regular_txs) + len(erc20_txs)

    # Расчет суммарного оборота в USD
    total_volume_usd = 0

    # Обработка обычных транзакций
    for transaction in regular_txs:
        tx_value_usd = calculate_transaction_value_in_usd(transaction, web3_instance=web3_instance)
        total_volume_usd += tx_value_usd
    
    # Обработка ERC-20 транзакций
    for transaction in erc20_txs:
        tx_value_usd = calculate_transaction_value_in_usd(transaction, is_erc20=True, web3_instance=web3_instance)
        total_volume_usd += tx_value_usd
   
    # Добавляем получение балансов
    # ВАЖНОЕ ИЗМЕНЕНИЕ: Безопасный вызов с проверкой web3_instance
    native_balance = get_wallet_balance(address, web3_instance) if web3_instance else None
    erc20_balances = get_erc20_token_balances(address, web3_instance) if web3_instance else []
 
    # Формирование сводки
    summary = {
        "address": address,
        "creation_date": creation_date,
        "analysis_period": f"{start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}",
        "transactions_last_month": total_tx_count,
        "regular_transactions": len(regular_txs),
        "erc20_transactions": len(erc20_txs),
        "total_volume_usd": round(total_volume_usd, 2),
        "native_balance": native_balance,
        "erc20_balances": erc20_balances
    }
    
    return summary

def get_wallet_balance(address, web3_instance):
    """
    Получение баланса кошелька в нативной валюте (MATIC)
    """
    
    address = ensure_checksum_address(address)

    try:
        # Получение баланса в MATIC
        balance_wei = web3_instance.eth.get_balance(address)
        balance_matic = web3_instance.from_wei(balance_wei, 'ether')
        
        # Получение текущей цены MATIC в USD
        matic_price = get_token_price_in_usd("0x0000000000000000000000000000000000000000")
        balance_usd = float(balance_matic) * matic_price
        
        return {
            "balance_matic": round(float(balance_matic), 4),
            "balance_usd": round(balance_usd, 2)
        }
    except Exception as e:
        print(f"Ошибка при получении баланса MATIC: {e}")
        return {
            "balance_matic": 0,
            "balance_usd": 0
        }

def get_erc20_token_balances(address, web3_instance):
    """
    Получение балансов ERC-20 токенов
    """
    # Словарь известных токенов с их ABI и декодированием
    token_info = {
        Web3.to_checksum_address("0x2791bca1f2de4661ed88a30c99a7a9449aa84174"): {
            "symbol": "USDCe",
            "decimals": 6
        },
        Web3.to_checksum_address("0x8f3cf7ad23cd3cadbd9735aff958023239c6a063"): {
            "symbol": "DAI",
            "decimals": 18
        },
        Web3.to_checksum_address("0xc2132d05d31c914a87c6611c10748aeb04b58e8f"): {
            "symbol": "USDT",
            "decimals": 6
        },
        Web3.to_checksum_address("0x3c499c542cef5e3811e1192ce70d8cc03d5c3359"): {
            "symbol": "USDC",
            "decimals": 6
        }
    }

    # Ensure address is in checksum format
    address = Web3.to_checksum_address(address)

    erc20_balances = []

    for token_address, token_details in token_info.items():
        try:
            # ABI для получения баланса и символа токена
            abi = [{
                "constant": True,
                "inputs": [{"name": "_owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "balance", "type": "uint256"}],
                "type": "function"
            }]

            # Создание контракта
            token_contract = web3_instance.eth.contract(address=token_address, abi=abi)

            # Получение баланса
            balance_raw = token_contract.functions.balanceOf(address).call()
            
            # Конвертация баланса с учетом decimals
            balance = balance_raw / (10 ** token_details["decimals"])
            
            # Получение цены токена
            token_price = get_token_price_in_usd(token_address)
            balance_usd = balance * token_price

            if balance > 0:
                erc20_balances.append({
                    "token": token_details["symbol"],
                    "balance": round(balance, 4),
                    "balance_usd": round(balance_usd, 2),
                    "price_usd": round(token_price, 4)
                })

        except Exception as e:
            print(f"Ошибка при получении баланса {token_details['symbol']}: {e}")

    return erc20_balances

if __name__ == "__main__":
    print("Пытаемся подключиться к Polygon...")
    
    # Попытка подключения к Web3
    web3 = get_web3_connection()
    
    # Если не удалось подключиться через Web3, продолжаем только с API
    if web3:
        print("Успешное подключение к Polygon через Web3")
    else:
        print("Продолжаем работу только через Polygonscan API") 
  
    # Получение и вывод сводки
    print(f"Анализ кошелька: {WALLET_ADDRESS}")
    wallet_summary = generate_wallet_summary(WALLET_ADDRESS, web3)

    print("\n===== СВОДКА ПО КОШЕЛЬКУ =====")
    print(f"Адрес: {wallet_summary['address']}")
    print(f"Дата создания кошелька: {wallet_summary['creation_date']}")
    print(f"Период анализа: {wallet_summary['analysis_period']} (30 дней)")
    print(f"Всего транзакций за период: {wallet_summary['transactions_last_month']}")
    print(f" - Обычных транзакций: {wallet_summary['regular_transactions']}")
    print(f" - ERC-20 транзакций: {wallet_summary['erc20_transactions']}")
    # Print native balance
    if wallet_summary.get("native_balance"):
        print("\nCurrent Balance:")
        print(f"MATIC: {wallet_summary['native_balance']['balance_matic']} (${wallet_summary['native_balance']['balance_usd']})")
       
    # Print ERC-20 balances
    if wallet_summary.get("erc20_balances"):
        print("\nToken Balances:")
        for token in wallet_summary['erc20_balances']:
            print(f"{token['token']}: {token['balance']} (${token['balance_usd']} at ${token['price_usd']}/token)")
    print(f"Суммарный оборот за период: ${wallet_summary['total_volume_usd']}")
    print("==============================")

