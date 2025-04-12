from binance import ThreadedWebsocketManager
from datetime import datetime

def calc_imbalance(bids, asks):
    bid_volume = sum(float(qty) for price, qty in bids[:5])
    ask_volume = sum(float(qty) for price, qty in asks[:5])
    imbalance = (bid_volume - ask_volume) / (bid_volume + ask_volume + 1e-6)
    return round(imbalance, 4)

def handle_order_book(msg):
    bids = msg['b']
    asks = msg['a']
    imbalance = calc_imbalance(bids, asks)

    now = datetime.now()
    print(f"[{now.strftime('%H:%M:%S')}] Imbalance: {imbalance:.4f}")

# --- Binance WebSocket ---
api_key = '9oMd3Ehs5oLzckNUTUn5ncaHENyzYTjVD6UQEHzmPIklyafdhP7UbO6U0cWEqjEF'
api_secret = ' XYCNHpc4egWSXG08fcnG1t9C2Uwufxe24mOwxK2nvYzioNSLbpuy2VOByGeLxRtd'
symbol = 'btcusdc'

bsm = ThreadedWebsocketManager(api_key=api_key, api_secret=api_secret)
bsm.start()
bsm.start_depth_socket(callback=handle_order_book, symbol=symbol.upper())
bsm.join()
