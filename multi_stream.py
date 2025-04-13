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

import queue
from threading import Thread
from datetime import datetime
from collections import deque, defaultdict
import numpy as np
from sklearn.linear_model import LinearRegression
import traceback

from strategy import should_buy, should_sell, record_buy_signal, record_sell_signal, get_open_position, init_mongo_connection
from symbols import get_top_volume_symbols
from trend import print_trend_info
from binance import ThreadedWebsocketManager
import os
from dotenv import load_dotenv
import requests
import time

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"[Telegram Error] {e}")

def heartbeat():
    while True:
        try:
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            send_telegram_message(f"✅ Bot is alive. Heartbeat @ {now}")
        except Exception as e:
            print(f"[Heartbeat Error] {e}")
        time.sleep(3600)  # 1 godzina

def test_mongo_connection(mongo_db):
    try:
        mongo_db.command("ping")
        msg = "✅ MongoDB connection successful."
        print(msg)
        send_telegram_message(msg)
    except Exception as e:
        msg = f"❌ MongoDB connection FAILED: {e}"
        print(msg)
        send_telegram_message(msg)

load_dotenv()

api_key = os.getenv("BINANCE_API_KEY")
api_secret = os.getenv("BINANCE_API_SECRET")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

mongo_db = init_mongo_connection()
test_mongo_connection(mongo_db)

rolling_window = 5
trade_buffers = defaultdict(list)
symbol_price_windows = defaultdict(lambda: deque(maxlen=30))
latest_imbalance = {}

trade_queue = queue.Queue()
orderbook_queue = queue.Queue()



def handle_trade(msg):
    trade_queue.put(msg)

def handle_order_book(msg):
    orderbook_queue.put(msg)

def local_fear_index(imbalance, volume_ratio, slope):
    fear = 0
    if imbalance < -0.3:
        fear += 1
    if volume_ratio < 0.8:
        fear += 1
    if slope is not None and slope < 0:
        fear += 1
    return fear

def trade_worker():
    while True:
        msg = trade_queue.get()
        try:
            if msg.get("e") == "error":
                print(f"[Binance Error] {msg}")
                continue

            symbol = msg.get('s')
            if symbol is None:
                raise ValueError(f"Invalid message format, missing 's': {msg}")

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
            trade_buffers[symbol] = [t for t in trade_buffers[symbol] if (timestamp - t['timestamp']).total_seconds() <= rolling_window]

            buy_vol = sum(t['qty'] for t in trade_buffers[symbol] if t['side'] == 'BUY')
            sell_vol = sum(t['qty'] for t in trade_buffers[symbol] if t['side'] == 'SELL')
            volume_ratio = buy_vol / (sell_vol + 1e-6)

            print(f"[{timestamp.strftime('%H:%M:%S')}] {symbol} BUY VOL: {buy_vol:.4f}, SELL VOL: {sell_vol:.4f}, RATIO: {volume_ratio:.2f}")

            symbol_price_windows[symbol].append(price)
            slope = None
            if len(symbol_price_windows[symbol]) >= 10:
                log_prices = np.log(symbol_price_windows[symbol])
                X = np.arange(len(log_prices)).reshape(-1, 1)
                model = LinearRegression().fit(X, log_prices)
                slope = model.coef_[0]
                direction = '⬆️' if slope > 0 else '⬇️'
                print(f"[{timestamp.strftime('%H:%M:%S')}] {symbol} Trend Slope: {slope:.6f} {direction}")
                print_trend_info()

            imbalance = latest_imbalance.get(symbol)
            if imbalance is not None:
                fear = local_fear_index(imbalance, volume_ratio, slope)
                if fear >= 2:
                    continue

                if should_buy(imbalance, volume_ratio, slope):
                    if not get_open_position(mongo_db, symbol):
                        record_buy_signal(mongo_db, symbol, price, imbalance, volume_ratio, slope, fear)
                        message = (
                            f"📈 BUY SIGNAL for {symbol}\n"
                            f"Price: {price:.2f}\n"
                            f"Imbalance: {imbalance:.2f}\n"
                            f"Volume Ratio: {volume_ratio:.2f}\n"
                            f"Slope: {slope:.6f}\n"
                            f"Fear Index: {fear} → Greed/Zaufanie"
                        )

                        print(message)
                        send_telegram_message(message)
                elif should_sell(imbalance, volume_ratio, slope):
                    if get_open_position(mongo_db, symbol):
                        record_sell_signal(mongo_db, symbol, price, imbalance, volume_ratio, slope, fear)
                        message = (
                                f"📉 SELL SIGNAL for {symbol}"
                                f"Price: {price:.2f}"
                                f"Imbalance: {imbalance:.2f}"
                                f"Volume Ratio: {volume_ratio:.2f}"
                                f"Slope: {slope:.6f}"
                                f"Fear Index: {fear} → Pozycja zamknięta w warunkach rynkowych"
                            )
                        print(message)
                        send_telegram_message(message)
        except Exception as e:
            error_message = f"❗ ERROR in trade_worker\nRaw msg: {msg}\n{traceback.format_exc()}"
            print(error_message)
            send_telegram_message(error_message)
        finally:
            trade_queue.task_done()

def orderbook_worker():
    while True:
        msg = orderbook_queue.get()
        try:
            symbol = msg['s']
            bids = msg['b']
            asks = msg['a']
            bid_volume = sum(float(qty) for price, qty in bids[:5])
            ask_volume = sum(float(qty) for price, qty in asks[:5])
            imbalance = (bid_volume - ask_volume) / (bid_volume + ask_volume + 1e-6)
            latest_imbalance[symbol] = imbalance
            timestamp = datetime.now().strftime('%H:%M:%S')
            print(f"[{timestamp}] {symbol} Imbalance: {imbalance:.4f}")
        except Exception as e:
            error_message = f"❗ ERROR in orderbook_worker\nRaw msg: {msg}\n{traceback.format_exc()}"
            print(error_message)
            send_telegram_message(error_message)
        finally:
            orderbook_queue.task_done()

Thread(target=trade_worker, daemon=True).start()
Thread(target=orderbook_worker, daemon=True).start()
Thread(target=heartbeat, daemon=True).start()


def main():
    try:
        top_symbols = get_top_volume_symbols(10)
        print("[INFO] Monitoring pairs:", top_symbols)

        bsm = ThreadedWebsocketManager(api_key=api_key, api_secret=api_secret)
        bsm.start()

        for symbol in top_symbols:
            bsm.start_trade_socket(callback=handle_trade, symbol=symbol.lower())
            bsm.start_depth_socket(callback=handle_order_book, symbol=symbol.upper())

        bsm.join()
    except Exception as e:
        error_message = f"❗ ERROR in main loop\n{traceback.format_exc()}"
        print(error_message)
        send_telegram_message(error_message)

if __name__ == '__main__':
    main()
