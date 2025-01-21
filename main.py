import asyncio
import websockets
import json
import time
from web3 import Web3


web3 = Web3(Web3.HTTPProvider("https://mainnet.infura.io/v3/8a9b4912e9ed412bba61112afbf29162"))


pair_address = '0xB4e16d0168e52d35CaCD2c6185b44281Ec28C9Dc'  


pair_abi = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "sender", "type": "address"},
            {"indexed": False, "internalType": "uint256", "name": "amount0In", "type": "uint256"},
            {"indexed": False, "internalType": "uint256", "name": "amount1In", "type": "uint256"},
            {"indexed": False, "internalType": "uint256", "name": "amount0Out", "type": "uint256"},
            {"indexed": False, "internalType": "uint256", "name": "amount1Out", "type": "uint256"},
            {"indexed": True, "internalType": "address", "name": "to", "type": "address"}
        ],
        "name": "Swap",
        "type": "event"
    }
]


pair_contract = web3.eth.contract(address=Web3.to_checksum_address(pair_address), abi=pair_abi)


last_processed_block = web3.eth.block_number


def calculate_ohlc(swap_events):
    prices = []
    for event in swap_events:
        args = event['args']
        if args['amount0In'] > 0:
            price = args['amount1Out'] / args['amount0In']
        elif args['amount1In'] > 0:
            price = args['amount0Out'] / args['amount1In']
        else:
            continue
        prices.append(price)

    if not prices:
        return None

    return {
        "timestamp": int(time.time()), 
        "open": prices[0],
        "high": max(prices),
        "low": min(prices),
        "close": prices[-1]
    }


def fetch_swap_events_for_block_range(from_block, to_block):
    events = pair_contract.events.Swap.create_filter(
        from_block=from_block, to_block=to_block
    ).get_all_entries()

    ohlc = calculate_ohlc(events)
    if ohlc:
        return ohlc
    else:
        return None


async def monitor_new_blocks(websocket):
    global last_processed_block
    while True:
        latest_block = web3.eth.block_number
        if latest_block > last_processed_block:
            print(f"New Block: {latest_block}")
            ohlc = fetch_swap_events_for_block_range(last_processed_block + 1, latest_block)
            message = {
                "event": "newBlock",
                "blockNumber": latest_block,
                "ohlc": ohlc if ohlc else None
            }
            
            await websocket.send(json.dumps(message))
            last_processed_block = latest_block
        
        await asyncio.sleep(10)  


async def handler(websocket, path):
    print("Client connected")
    

    await monitor_new_blocks(websocket)


async def main():
    async with websockets.serve(handler, "0.0.0.0", 3000):
        print("WebSocket server running on ws://localhost:3000")
        await asyncio.Future()  # run forever

if __name__ == '__main__':
    asyncio.run(main())
