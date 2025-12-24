FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Usa gunicorn (mejor para producción)
CMD ["gunicorn", "--bind", "0.0.0.0:$PORT", "webhook_server:app"]