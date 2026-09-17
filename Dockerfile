FROM python:3.12-slim

# Системные библиотеки для WeasyPrint + шрифты
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    libcairo2 \
    libpangoft2-1.0-0 \
    fonts-liberation \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Сначала зависимости (чтобы кэшировалось)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Потом весь код
COPY . .

# Папка для базы (если будешь использовать volume)
RUN mkdir -p /app/data

CMD ["python", "main.py"]