from binance import ThreadedWebsocketManager
from datetime import datetime
from trend import add_price, print_trend_info
import pandas as pd

# --- Dane do rolling volume ---
rolling_window = 5  # sekund
trades = []

def handle_trade(msg):
    global trades
    timestamp = datetime.fromtimestamp(msg['T'] / 1000)
    price = float(msg['p'])
    qty = float(msg['q'])
    is_buyer_maker = msg['m']  # True = SELL (market), False = BUY (market)

    trade = {
        'timestamp': timestamp,
        'price': price,
        'qty': qty,
        'side': 'BUY' if not is_buyer_maker else 'SELL'
    }

    trades.append(trade)

    # rolling window (5s)
    trades = [t for t in trades if (timestamp - t['timestamp']).total_seconds() <= rolling_window]

    buy_vol = sum(t['qty'] for t in trades if t['side'] == 'BUY')
    sell_vol = sum(t['qty'] for t in trades if t['side'] == 'SELL')
    volume_ratio = buy_vol / (sell_vol + 1e-6)

    print(f"[{timestamp.strftime('%H:%M:%S')}] BUY VOL: {buy_vol:.4f}, SELL VOL: {sell_vol:.4f}, RATIO: {volume_ratio:.2f}")

    # ⬇️ Dodaj analizę trendu
    add_price(price)
    print_trend_info()


# --- Binance WebSocket ---
api_key = '9oMd3Ehs5oLzckNUTUn5ncaHENyzYTjVD6UQEHzmPIklyafdhP7UbO6U0cWEqjEF'
api_secret = ' XYCNHpc4egWSXG08fcnG1t9C2Uwufxe24mOwxK2nvYzioNSLbpuy2VOByGeLxRtd'
symbol = 'btcusdc'

bsm = ThreadedWebsocketManager(api_key=api_key, api_secret=api_secret)
bsm.start()
bsm.start_trade_socket(callback=handle_trade, symbol=symbol.upper())

bsm.join()
