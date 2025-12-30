import logging
from typing import Any, Dict

import pandas as pd  # pyright: ignore[reportMissingImports]

logger = logging.getLogger("TestUtils")


class _SimpleRedis:
    """Простейшая реализация get/set/delete для тестов.

    Предоставляет минимальный интерфейс, который используется стратегиями/оркестратором:
    - get(key) -> value or None
    - set(key, value)
    - delete(key)
    """

    def __init__(self):
        self._store: Dict[str, Any] = {}

    def get(self, key: str):
        return self._store.get(key)

    def set(self, key: str, value: Any):
        self._store[key] = value

    def delete(self, key: str):
        if key in self._store:
            del self._store[key]


class MockBus:
    """In-memory pub/sub для тестов.

    Поведение:
    - хранит подписчиков в памяти (topic -> [handlers])
    - при `publish` синхронно вызывает зарегистрированные обработчики
    - сохраняет историю опубликованных сообщений в `published`
    - предоставляет объект `redis` с get/set/delete для тестов
    """

    def __init__(self):
        # topic -> [handler]
        self._subscribers: dict = {}
        # список кортежей (topic, data) для проверок в тестах
        self.published: list = []
        # объект с интерфейсом get/set/delete, совместимый с кодом, ожидающим redis-подобный объект
        self.redis = _SimpleRedis()

    def publish(self, topic, data):
        # Сохраняем для тестовой инспекции
        try:
            self.published.append((topic, data))
            handlers = list(self._subscribers.get(topic, []))
            for handler in handlers:
                try:
                    handler(data)
                except Exception as e:
                    # Логируем и пробрасываем, чтобы тесты могли увидеть ошибку
                    logger.exception(f"Error in handler for topic '{topic}': {e}")
                    raise
        except Exception:
            # Защита от неожиданных ошибок при публикации
            raise

    def subscribe(self, topic, handler):
        self._subscribers.setdefault(topic, []).append(handler)

    def start(self):
        # Ничего асинхронного не требуется для синхронных тестов
        return


class TestDataProvider:
    def __init__(self, http_client):
        self.http = http_client

    def get_test_historical_data(
        self, symbol: str, interval: str = "5", limit: int = 200
    ) -> pd.DataFrame:
        try:
            response = self.http.get_kline(
                category="linear", symbol=symbol, interval=interval, limit=limit
            )
            if response["retCode"] == 0:
                data = response["result"]["list"]
                df = pd.DataFrame(
                    data,
                    columns=[
                        "timestamp",
                        "open",
                        "high",
                        "low",
                        "close",
                        "volume",
                        "turnover",
                    ],
                )
                df["timestamp"] = pd.to_numeric(df["timestamp"])
                df["open"] = pd.to_numeric(df["open"])
                df["high"] = pd.to_numeric(df["high"])
                df["low"] = pd.to_numeric(df["low"])
                df["close"] = pd.to_numeric(df["close"])
                df["volume"] = pd.to_numeric(df["volume"])
                df = df.sort_values("timestamp").reset_index(drop=True)
                # Set index to datetime for indicators
                df.set_index(
                    pd.to_datetime(df["timestamp"], unit="ms", utc=True), inplace=True
                )
                return df
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Error fetching history: {e}")
            return pd.DataFrame()

    def get_test_indicators_for_plotting(self) -> Dict[str, Any]:
        """
        Возвращает словарь с индикаторами для построения графиков.
        """
        return {
            "main": {
                "st_trend": {
                    "color": "yellow",
                    "linestyle": "-",
                    "label": "ST Trend",
                },
                "highex": {
                    "color": "blue",
                    "marker": "^",
                    "label": "High Ex",
                },
                "lowex": {
                    "color": "orange",
                    "marker": "v",
                    "label": "Low Ex",
                },
            },
            "volume": {
                "volume": {
                    "color": "gray",
                    "linestyle": "histogram",
                    "label": "Volume",
                },
                "volsma": {
                    "color": "red",
                    "linestyle": "-",
                    "label": "Vol SMA",
                },
            },
            "NATR": {
                "natr": {
                    "color": "red",
                    "linestyle": "-",
                    "label": "NATR",
                },
            },
            "stochRSI": {
                "stochk": {
                    "color": "green",
                    "linestyle": "-",
                    "label": "Stoch K",
                },
                "stochd": {
                    "color": "red",
                    "linestyle": "--",
                    "label": "Stoch D",
                },
                # Дополнительные горизонтальные линии для отдельных графиков
                "stochrsi_overbought": {
                    "value": 80,
                    "color": "black",
                    "linestyle": ":",
                    "label": "Overbought",
                },
                "stochrsi_oversold": {
                    "value": 20,
                    "color": "black",
                    "linestyle": ":",
                    "label": "Oversold",
                },
            }
        }
