FROM python:3.9-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY services /app/services
COPY strategies/top_trend_breakout /app/strategy
ENV PYTHONPATH=/app
CMD ["python", "strategy/main.py"]
