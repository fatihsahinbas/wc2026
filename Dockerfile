FROM python:3.12-slim

WORKDIR /app

# Bağımlılıkları önce kopyala (cache için)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama kodunu kopyala
COPY . .

# Instance klasörü (SQLite DB buraya yazılır)
RUN mkdir -p instance

EXPOSE 8000

ENV FLASK_APP=run.py
ENV FLASK_ENV=production

CMD ["gunicorn", "run:app", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "120"]
