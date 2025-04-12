from datetime import datetime
from uuid import uuid4
from pymongo import MongoClient
import os

# === MongoDB ===
def init_mongo_connection():
    mongo_uri = os.getenv("MONGO_URI")
    client = MongoClient(mongo_uri)
    db = client["sparx_trading"]
    return db

# === Logika strategii ===
def should_buy(imbalance, volume_ratio, slope):
    return (
        imbalance > 0.35 and
        volume_ratio > 1.5 and
        slope is not None and slope > 0.001
    )

def should_sell(imbalance, volume_ratio, slope):
    return (
        imbalance < -0.35 and
        volume_ratio < 0.65 and
        slope is not None and slope < -0.001
    )

# === Zapis BUY ===
def record_buy_signal(mongo_db, symbol, price, imbalance, volume_ratio, slope):
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
        "timestamp": timestamp
    })
    return trade_id

# === Zapis SELL ===
def record_sell_signal(mongo_db, symbol, price, imbalance, volume_ratio, slope):
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
