from binance.client import Client

EXCLUDED_PAIRS = ['TRY', 'USDT', 'BUSD', 'TUSD', 'FDUSD', 'DAI', 'EUR', 'GBP','PLN','JPY','ARS','BRL']

def is_stablecoin_pair(symbol):
    return any(stable in symbol for stable in EXCLUDED_PAIRS)

def get_top_volume_symbols(limit=20):
    client = Client()

    # Pobieramy dane o tickerach (24h volume)
    tickers = client.get_ticker()

    # Filtrowanie: odrzucamy stablecoinowe pary
    tradable_pairs = [t for t in tickers if not is_stablecoin_pair(t['symbol'])]

    # Sortujemy po wolumenie
    top_volume = sorted(tradable_pairs, key=lambda x: float(x['quoteVolume']), reverse=True)

    # Zwracamy tylko symbole
    top_symbols = [t['symbol'] for t in top_volume[:limit]]
    return top_symbols

if __name__ == "__main__":
    top_symbols = get_top_volume_symbols()
    print("Top coinów wg 24h volume bez stablecoinów:")
    for s in top_symbols:
        print(" -", s)