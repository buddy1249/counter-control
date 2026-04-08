FROM python:3.11-slim

WORKDIR /app

# Создаем пользователя appuser с ID 1000
RUN useradd -m -u 1000 appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код и меняем владельца на appuser
COPY --chown=appuser:appuser . .

# Переключаемся на безопасного пользователя
USER appuser

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
