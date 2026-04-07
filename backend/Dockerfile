FROM python:3.10-slim

# Katalog roboczy w kontenerze
WORKDIR /app

# Kopiujemy listę bibliotek z głównego folderu
COPY requirements.txt .

# Instalacja bibliotek
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install psycopg2-binary

# Kopiujemy kod backendu
COPY backend/ ./backend/

# Komenda odpalająca serwer FastAPI
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]