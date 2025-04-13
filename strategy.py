from datetime import datetime
from uuid import uuid4
from pymongo import MongoClient
import os
import numpy as np
from sklearn.linear_model import LinearRegression

# === MongoDB ===
def init_mongo_connection():
    mongo_uri = os.getenv("MONGO_URI")
    client = MongoClient(mongo_uri)
    db = client["sparx_trading"]
    return db

# === Logika strategii ===
def should_buy(imbalance, volume_ratio, slope):
    return (
        imbalance > 0.25 and
        volume_ratio > 1.2 and
        slope is not None and slope > 0.0005
    )

def should_sell(imbalance, volume_ratio, slope):
    return (
        imbalance < -0.25 and
        volume_ratio < 0.8 and
        slope is not None and slope < -0.0005
    )

# === Zapis BUY ===
def record_buy_signal(mongo_db, symbol, price, imbalance, volume_ratio, slope, fear, divergence):
    trade_id = str(uuid4())
    timestamp = datetime.utcnow()
    mongo_db.signals.insert_one({
        "trade_id": trade_id,
        "symbol": symbol,
        "signal_type": "BUY",
        "price": price,
        "imbalance": imbalance,
        "volume_ratio": volume_ratio,
        "slope": slope,
        "fear_index": fear,
        "divergence": divergence,
        "timestamp": timestamp
    })
    return trade_id

# === Zapis SELL ===
def record_sell_signal(mongo_db, symbol, price, imbalance, volume_ratio, slope, fear, divergence):
    last_buy = mongo_db.signals.find_one({
        "symbol": symbol,
        "signal_type": "BUY"
    }, sort=[("timestamp", -1)])

    if last_buy and not mongo_db.signals.find_one({"signal_type": "SELL", "trade_id": last_buy["trade_id"]}):
        buy_price = last_buy["price"]
        profit_pct = ((price - buy_price) / buy_price) * 100
        mongo_db.signals.insert_one({
            "trade_id": last_buy["trade_id"],
            "symbol": symbol,
            "signal_type": "SELL",
            "price": price,
            "imbalance": imbalance,
            "volume_ratio": volume_ratio,
            "slope": slope,
            "fear_index": fear,
            "divergence": divergence,
            "timestamp": datetime.utcnow(),
            "profit_pct": profit_pct
        })
        return True
    return False

# === Sprawdzenie pozycji otwartej ===
def get_open_position(mongo_db, symbol):
    last_buy = mongo_db.signals.find_one({
        "symbol": symbol,
        "signal_type": "BUY"
    }, sort=[("timestamp", -1)])

    if last_buy:
        sell_exists = mongo_db.signals.find_one({
            "signal_type": "SELL",
            "trade_id": last_buy["trade_id"]
        })
        if not sell_exists:
            return last_buy

    return None

# === Dywergencja z trendem długo-/krótkoterminowym ===
def calculate_trend_divergence(price_window):
    if len(price_window) < 20:
        return None

    short_window = np.array(price_window)[-10:]
    long_window = np.array(price_window)[-20:]

    log_short = np.log(short_window)
    log_long = np.log(long_window)

    X_short = np.arange(len(log_short)).reshape(-1, 1)
    X_long = np.arange(len(log_long)).reshape(-1, 1)

    slope_short = LinearRegression().fit(X_short, log_short).coef_[0]
    slope_long = LinearRegression().fit(X_long, log_long).coef_[0]

    divergence = slope_short - slope_long
    return {
        "slope_short": slope_short,
        "slope_long": slope_long,
        "divergence": divergence
    }
