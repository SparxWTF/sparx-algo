from binance.client import Client

def get_top_volume_symbols(limit=10):
    client = Client()

    # Pobieramy dane o tickerach (24h volume)
    tickers = client.get_ticker()

    # Filtrowanie tylko USDT par i usunięcie stablecoinów (opcjonalnie)
    usdt_pairs = [t for t in tickers if t['symbol'].endswith('USDT') and not t['symbol'].startswith('USD')]

    # Sortujemy po wolumenie w USDT
    top_volume = sorted(usdt_pairs, key=lambda x: float(x['quoteVolume']), reverse=True)

    # Zwracamy tylko nazwy symboli np. ['BTCUSDT', 'ETHUSDT', ...]
    top_symbols = [t['symbol'] for t in top_volume[:limit]]
    return top_symbols


if __name__ == "__main__":
    top_symbols = get_top_volume_symbols()
    print("Top 10 coinów wg 24h volume:")
    for s in top_symbols:
        print(" -", s)
