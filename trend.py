import numpy as np
from sklearn.linear_model import LinearRegression
from collections import deque
from datetime import datetime

# 🧠 Parametry konfiguracyjne
ROLLING_WINDOW = 30  # liczba ostatnich ticków do analizy

# 📦 Bufor cen do regresji
price_window = deque(maxlen=ROLLING_WINDOW)

def add_price(price: float):
    """
    Dodaje cenę do rolling listy.
    """
    price_window.append(price)

def get_trend_slope() -> float | None:
    """
    Zwraca nachylenie regresji liniowej log(price).
    """
    if len(price_window) < 10:
        return None  # za mało danych do analizy

    log_prices = np.log(price_window)
    X = np.arange(len(log_prices)).reshape(-1, 1)
    model = LinearRegression().fit(X, log_prices)
    slope = model.coef_[0]
    return slope

def get_trend_direction(slope: float) -> str:
    """
    Interpretacja trendu.
    """
    if slope > 0.0005:
        return "⬆️ UPTREND"
    elif slope < -0.0005:
        return "⬇️ DOWNTREND"
    else:
        return "➖ NEUTRAL"

def print_trend_info():
    """
    Wypisuje pełne info o trendzie.
    """
    slope = get_trend_slope()
    if slope is not None:
        direction = get_trend_direction(slope)
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] Trend Slope: {slope:.6f}   {direction}")
