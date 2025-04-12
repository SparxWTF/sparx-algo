"""
This module implements a multi-stream cryptocurrency trading data collector using Binance API.

It monitors multiple trading pairs for real-time trade and order book data,
calculates various metrics such as buy/sell volume ratios and order book imbalances,
and performs trend analysis on price movements.

Key components:
- Binance WebSocket connections for multiple symbols
- Real-time trade and order book data processing
- Rolling window calculations for volume analysis
- Linear regression for trend analysis

Dependencies:
- binance
- datetime
- collections
- trend (custom module)
- symbols (custom module)
- numpy
- sklearn
"""

from binance import ThreadedWebsocketManager, Client
from datetime import datetime
from collections import deque, defaultdict
from trend import add_price, print_trend_info, price_window
from symbols import get_top_volume_symbols
from dotenv import load_dotenv
import os

load_dotenv()

api_key = os.getenv('BINANCE_API_KEY')
api_secret = os.getenv('BINANCE_API_SECRET')

# --- Globalne struktury danych ---
rolling_window = 5  # sekundy do liczenia buy/sell volume
trade_buffers = defaultdict(list)  # {symbol: [trades]}

# --- Inicjalizacja trendów per symbol ---
symbol_price_windows = defaultdict(lambda: deque(maxlen=30))


# --- CALLBACK: Time & Sales ---
def handle_trade(msg):
    symbol = msg['s']
    timestamp = datetime.fromtimestamp(msg['T'] / 1000)
    price = float(msg['p'])
    qty = float(msg['q'])
    is_buyer_maker = msg['m']
    side = 'BUY' if not is_buyer_maker else 'SELL'

    trade = {
        'timestamp': timestamp,
        'price': price,
        'qty': qty,
        'side': side
    }

    trade_buffers[symbol].append(trade)
    trade_buffers[symbol] = [t for t in trade_buffers[symbol] if
                             (timestamp - t['timestamp']).total_seconds() <= rolling_window]

    buy_vol = sum(t['qty'] for t in trade_buffers[symbol] if t['side'] == 'BUY')
    sell_vol = sum(t['qty'] for t in trade_buffers[symbol] if t['side'] == 'SELL')
    volume_ratio = buy_vol / (sell_vol + 1e-6)

    print(
        f"[{timestamp.strftime('%H:%M:%S')}] {symbol} BUY VOL: {buy_vol:.4f}, SELL VOL: {sell_vol:.4f}, RATIO: {volume_ratio:.2f}")

    # Trend per symbol
    symbol_price_windows[symbol].append(price)
    if len(symbol_price_windows[symbol]) >= 10:
        log_prices = np.log(symbol_price_windows[symbol])
        X = np.arange(len(log_prices)).reshape(-1, 1)
        model = LinearRegression().fit(X, log_prices)
        slope = model.coef_[0]
        direction = '⬆️' if slope > 0 else '⬇️'
        print(f"[{timestamp.strftime('%H:%M:%S')}] {symbol} Trend Slope: {slope:.6f} {direction}")


# --- CALLBACK: Order Book ---
def handle_order_book(msg):
    symbol = msg['s']
    bids = msg['b']
    asks = msg['a']
    bid_volume = sum(float(qty) for price, qty in bids[:5])
    ask_volume = sum(float(qty) for price, qty in asks[:5])
    imbalance = (bid_volume - ask_volume) / (bid_volume + ask_volume + 1e-6)
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"[{timestamp}] {symbol} Imbalance: {imbalance:.4f}")


# --- URUCHOMIENIE STREAMÓW ---
def main():
    top_symbols = get_top_volume_symbols(10)
    print("[INFO] Monitoring pairs:", top_symbols)

    bsm = ThreadedWebsocketManager(api_key=api_key, api_secret=api_secret)
    bsm.start()

    for symbol in top_symbols:
        bsm.start_trade_socket(callback=handle_trade, symbol=symbol.lower())
        bsm.start_depth_socket(callback=handle_order_book, symbol=symbol.lower())

    bsm.join()


if __name__ == '__main__':
    import numpy as np
    from sklearn.linear_model import LinearRegression

    main()
