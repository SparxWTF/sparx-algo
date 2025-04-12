# 🔧 Podstawowy Python image
FROM python:3.11-slim

# 🌍 Zmiana katalogu roboczego
WORKDIR /app

# 📦 Kopiujemy pliki
COPY . .

# ⚙️ Instalacja zależności
RUN pip install --no-cache-dir -r requirements.txt

# ▶️ Domyślne uruchomienie
CMD ["python", "multi_stream.py"]
