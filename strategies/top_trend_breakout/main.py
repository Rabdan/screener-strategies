"""
Стратегия TopTrendBreakOut (Топ Тренд Пробой).

Основная идея:
- Торговля по тренду (определяется SuperTrend) с подтверждением через локальные экстремумы (пробой уровней).
- Условия входа в Long:
    1. SuperTrend направлен вверх (st_dir > 0).
    2. Цена (Low текущего свинга) выше High предыдущего свинга (повышение минимумов/максимумов).
    3. Объем на текущем движении меньше объема на предыдущем (затухание коррекции/подтверждение структуры).
- Выход (SL): динамический, подтягивается по линии SuperTrend.
- Тейк-профит (TP): рассчитывается на основе волатильности последнего свинга.

Архитектура:
- Стратегия генерирует сигналы (StrategySignalEvent) и отправляет их в EventBus.
- ExecutionManager (или Backtester) принимает сигналы, считает риск и исполняет ордера.
- Стратегия получает обратную связь через OrderUpdateEvent и PositionUpdateEvent.
"""

import json
import logging
import os
import sys
import time
from typing import Any, Dict, List, Optional, Set

import numpy as np
import pandas as pd
import pandas_ta as ta
from pybit.unified_trading import HTTP

# Импорт событий и шины
# Используем try-import для поддержки запуска как из корня проекта, так и из папки стратегии
try:
    from services.bus import EventBus
    from services.events import (
        OrderUpdateEvent,
        PositionUpdateEvent,
        StrategySetTPSLEvent,
        StrategySignalEvent,
        CandleUpdateEvent,
        StrategyMetadata,
        get_meta_key,
        get_candles_key,
        CH_STRATEGY_EVENTS
    )
except ImportError:
    # Fallback для IDE или специфичных окружений
    from ...services.bus import EventBus
    from ...services.events import (
        OrderUpdateEvent,
        PositionUpdateEvent,
        StrategySetTPSLEvent,
        StrategySignalEvent,
        CandleUpdateEvent,
        StrategyMetadata,
        get_meta_key,
        get_candles_key,
        CH_STRATEGY_EVENTS
    )

try:
    from .indicators import Indicators
    from .test_utils import MockBus, TestDataProvider
except ImportError:
    from indicators import Indicators
    from test_utils import MockBus, TestDataProvider

# Конфигурация из переменных окружения
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
STRATEGY_ID = os.getenv("STRATEGY_ID", "TopTrendBreakOut")
STRATEGY_NAME = os.getenv("STRATEGY_NAME", "Top Trend Breakout")
TESTNET = os.getenv("BYBIT_TESTNET", "false").lower() == "true"
LOGS_DIR = os.getenv("LOGS_DIR", "logs")

# Настройка логирования
os.makedirs(LOGS_DIR, exist_ok=True)
log_file = os.path.join(LOGS_DIR, f"{STRATEGY_ID}.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(log_file), logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(STRATEGY_ID)


class TopTrendBreakOut:
    """
    Основной класс стратегии.
    """

    def __init__(self, test_mode: bool = False, symbol: str = "BTCUSDT"):
        """
        Инициализация стратегии.

        Параметры:
            test_mode (bool): Если True, использует MockBus и TestDataProvider.
            symbol (str): Символ по умолчанию.
        """
        self.test_mode = test_mode
        self.strategy_id = STRATEGY_ID
        self.default_symbol = symbol
        self.running = True

        # --- Параметры стратегии ---
        self.klines_interval = 5  # Таймфрейм (минуты)
        self.min_data_for_indicators = 100  # Длина истории для разогрева индикаторов
        self.rsi_period = 10
        self.risk_percent = 0.01  # Риск на сделку (1%)
        self.leverage = 5.0  # Кредитное плечо

        # Утилиты
        self.indicators = Indicators(rsi_period=self.rsi_period)

        # Подключение к инфраструктуре
        if not self.test_mode:
            self.bus = EventBus(host=REDIS_HOST)
            self.test_provider = None
        else:
            self.bus = MockBus()
            self.test_provider = None  # Инициализируется в run или тесте

        # --- Внутреннее состояние ---
        # Позиции: symbol -> размер (float)
        self.positions: Dict[str, float] = {}
        # Активные ордера: symbol -> {order_id: Event}
        self.active_orders: Dict[str, Dict[str, Any]] = {}
        # Рабочий набор символов (watchlist)
        self.working_symbols: Set[str] = set()

        # Таймеры
        self.last_ticker_update = 0
        self.last_candle_update = 0
        self.last_processed_timestamps: Dict[str, float] = {}

        # API клиент
        self.http = HTTP(testnet=TESTNET)
        if self.test_mode:
            self.test_provider = TestDataProvider(self.http)

    # -------------------------------------------------------------------------
    # Расчет индикаторов
    # -------------------------------------------------------------------------
    # calculate_indicators logic moved to get_historical_data

    # -------------------------------------------------------------------------
    # Торговая логика: Вход
    # -------------------------------------------------------------------------
    def check_entry_signals(self, df: pd.DataFrame, symbol: str = None):
        """
        Анализирует рынок на наличие сигналов входа.
        Отправляет StrategySignalEvent при выполнении условий.
        """
        if not symbol:
            symbol = self.default_symbol

        # Фильтр: не входим, если уже в позиции или висит ордер
        if self.positions.get(symbol, 0.0) != 0:
            return
        if self.active_orders.get(symbol):
            return

        if len(df) < self.min_data_for_indicators:
            return
        
        # Индикаторы уже рассчитаны в get_historical_data
        klines = df
        
        # Данные последней свечи
        try:
            current_kline = klines.iloc[-1]
            st_dir = current_kline.get("st_dir", np.nan)
            st_trend = current_kline.get("st_trend", np.nan)
            current_close = current_kline["close"]
        except Exception:
            return

        if pd.isna(st_dir) or pd.isna(st_trend):
            return

        # Поиск экстремумов
        try:
            max_high_indices, min_low_indices = self.indicators.find_stoch_extrema(klines)
        except Exception:
            return

        if len(min_low_indices) < 2 or len(max_high_indices) < 2:
            return

        # Индексы (время) последних свингов
        # last - самый последний сформированный, prev - предпоследний
        idx_low_last = min_low_indices[-1]
        idx_low_prev = min_low_indices[-2]
        idx_high_last = max_high_indices[-1]
        idx_high_prev = max_high_indices[-2]

        # Значения цен в экстремумах
        try:
            low_last = klines.loc[idx_low_last, "low"]
            # low_prev = klines.loc[idx_low_prev, "low"] # unused in logic below directly
            high_last = klines.loc[idx_high_last, "high"]
            high_prev = klines.loc[idx_high_prev, "high"]
            
            # Для Short логики
            low_prev_for_short = klines.loc[idx_low_prev, "low"]
        except KeyError:
            return

        # Функция расчета объема на свинге
        def get_vol_sum(idx1, idx2):
            start, end = min(idx1, idx2), max(idx1, idx2)
            try:
                return klines.loc[start:end, "volume"].sum()
            except Exception:
                return 0.0

        vol_last = get_vol_sum(idx_low_last, idx_high_last)
        vol_prev = get_vol_sum(idx_low_prev, idx_high_prev)

        # === ЛОНГ (Buy) ===
        # Условия:
        # 1. SuperTrend Up (st_dir > 0)
        # 2. Повышение структуры: Текущий Low > Предыдущий High (Low[Last] > High[Prev]) — сильный тренд
        # 3. Объем падает (VolLast < VolPrev)
        if st_dir > 0:
            if low_last > high_prev:
                if vol_last < vol_prev:
                    # TP = Размер последнего свинга, спроецированный от Low
                    task_profit = current_close * 1.02 # fallback
                    try:
                        low_prev_val = klines.loc[idx_low_prev, "low"]
                        task_profit = low_last + (high_last - low_prev_val) # Проекция амплитуды
                    except:
                        pass

                    sl = st_trend

                    logger.info(f"[{symbol}] Сигнал OPEN_LONG. Price={current_close}, SL={sl}, TP={task_profit}")
                    self.send_signal(symbol, "OPEN_LONG", price=current_close, stop_loss=sl, take_profit=task_profit)

        # === ШОРТ (Sell) ===
        # Условия:
        # 1. SuperTrend Down (st_dir < 0)
        # 2. Понижение структуры: Текущий High < Предыдущий Low
        # 3. Объем падает
        elif st_dir < 0:
            if high_last < low_prev_for_short:
                if vol_last < vol_prev:
                    # TP проекция вниз
                    task_profit = current_close * 0.98
                    try:
                        high_prev_val = klines.loc[idx_high_prev, "high"]
                        task_profit = high_last - (high_prev_val - low_last)
                    except:
                        pass

                    sl = st_trend

                    logger.info(f"[{symbol}] Сигнал OPEN_SHORT. Price={current_close}, SL={sl}, TP={task_profit}")
                    self.send_signal(symbol, "OPEN_SHORT", price=current_close, stop_loss=sl, take_profit=task_profit)

    # -------------------------------------------------------------------------
    # Торговая логика: Выход (Trailing SL)
    # -------------------------------------------------------------------------
    def check_exit_signals(self, df: pd.DataFrame, symbol: str = None):
        """
        Проверяет условия для обновления Stop Loss (Trailing).
        """
        if not symbol:
            symbol = self.default_symbol

        if self.positions.get(symbol, 0.0) == 0:
            return

        if df.empty:
            return

        klines = df

        current_kline = klines.iloc[-1]
        st_trend = current_kline.get("st_trend")

        if st_trend is not None and not pd.isna(st_trend):
            # Обновляем SL на уровень SuperTrend
            self.send_update_sl(symbol, float(st_trend))

    # -------------------------------------------------------------------------
    # Взаимодействие с системой (Signals & Events)
    # -------------------------------------------------------------------------
    def send_signal(
        self,
        symbol: str,
        action: str,
        price: float = None,
        close_percent: float = None,
        stop_loss: float = None,
        take_profit: float = None,
    ):
        """
        Формирует и публикует сигнал стратегии.
        """
        # Округление для API
        def safe_round(val, digits=8):
            try:
                return round(float(val), digits) if val is not None and not pd.isna(val) else None
            except Exception:
                return None

        signal = StrategySignalEvent(
            strategy_id=self.strategy_id,
            symbol=symbol,
            action=action,
            risk_pct=self.risk_percent if "OPEN" in action else None,
            close_percent=close_percent,
            price=safe_round(price),
            leverage=self.leverage,
            stop_loss=safe_round(stop_loss),
            take_profit=safe_round(take_profit),
        )

        try:
            self.bus.publish("StrategySignalEvent", signal.dict())
        except Exception as e:
            logger.error(f"Не удалось отправить сигнал: {e}")

    def send_update_sl(self, symbol: str, stop_loss: float):
        """Отправляет запрос на обновление SL."""
        try:
            sl_val = round(float(stop_loss), 4)
            event = StrategySetTPSLEvent(
                strategy_id=self.strategy_id, symbol=symbol, stop_loss=sl_val
            )
            self.bus.publish("StrategySetTPSLEvent", event.dict())
        except Exception as e:
            logger.error(f"Не удалось отправить обновление SL: {e}")

    # -------------------------------------------------------------------------
    # Работа с данными (Data Fetching)
    # -------------------------------------------------------------------------
    def apply_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Рассчитывает технические индикаторы для стратегии.
        """
        df = df.copy()

        # 1. Расчет NATR (Normalized Average True Range) для оценки волатильности
        df['natr'] = ta.natr(df['high'], df['low'], df['close'], length=14)

        # 2. StochRSI на Heiken Ashi — помогает фильтровать шум и находить зоны перепроданности/перекупленности
        try:
            df["stochK"], df["stochD"] = self.indicators._heiken_stochrsi(df, self.rsi_period, 3, 3)
        except:
            df["stochK"], df["stochD"] = np.nan, np.nan

        # 3. SuperTrend — наш основной фильтр тренда (Up/Down)
        try:
            st = ta.supertrend(df["high"], df["low"], df["close"], length=self.rsi_period, multiplier=2.5)
            if st is not None:
                st_col = f"SUPERT_{self.rsi_period}_2.5"
                std_col = f"SUPERTd_{self.rsi_period}_2.5"
                df["st_trend"] = st.get(st_col, np.nan) # Цена линии SuperTrend (используем как SL)
                df["st_dir"] = st.get(std_col, np.nan)   # Направление (1 для Long, -1 для Short)
        except:
            df["st_trend"], df["st_dir"] = np.nan, np.nan

        # 4. Вспомогательные индикаторы: ROC (Momentum), VolSMA (сглаживание объема), VWAP (якорь дня)
        try:
            df["ROC"] = ta.roc(df["close"], length=self.rsi_period)
            df["VolSMA"] = ta.sma(df["volume"], length=50)
            df["VWAP"] = ta.vwap(df["high"], df["low"], df["close"], df["volume"], anchor="D")
        except:
            pass

        return df

    def get_historical_data(self, symbol: str, limit: int = 200) -> pd.DataFrame:
        """Получает исторические данные и обогащает их индикаторами."""
        interval = str(self.klines_interval)
        
        # Пытаемся получить данные с биржи или провайдера тестов
        if self.test_mode and self.test_provider:
            df = self.test_provider.get_test_historical_data(symbol, interval, limit)
        else:
            try:
                response = self.http.get_kline(
                    category="linear", symbol=symbol, interval=interval, limit=limit
                )
                if response.get("retCode") == 0:
                    data = response.get("result", {}).get("list", [])
                    df = pd.DataFrame(data, columns=["timestamp", "open", "high", "low", "close", "volume", "turnover"])
                    cols = ["open", "high", "low", "close", "volume"]
                    df[cols] = df[cols].apply(pd.to_numeric, errors="coerce")
                    df["timestamp"] = pd.to_numeric(df["timestamp"])
                    df = df.sort_values("timestamp").reset_index(drop=True)
                    df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
                    df.set_index("datetime", inplace=True)
                else:
                    return pd.DataFrame()
            except Exception as e:
                logger.error(f"Исключение при получении данных: {e}")
                return pd.DataFrame()

        if df.empty:
            return df

        # Применяем расчет индикаторов (вынесено в отдельный метод)
        df = self.apply_indicators(df)

        # --- Логика обработки новой закрытой свечи ---
        last_kline = df.iloc[-1]
        ts = last_kline["timestamp"]
        
        # Если время свечи больше последнего обработанного, значит пришла новая порция данных
        if symbol not in self.last_processed_timestamps or ts > self.last_processed_timestamps[symbol]:
            self.last_processed_timestamps[symbol] = ts
            
            # 1. Собираем данные индикаторов для трансляции в UI
            indicators_data = {
                "st_trend": float(last_kline.get("st_trend", 0)),
                "st_dir": float(last_kline.get("st_dir", 0)),
                "stochK": float(last_kline.get("stochK", 0)),
                "stochD": float(last_kline.get("stochD", 0)),
                "ROC": float(last_kline.get("ROC", 0)),
                "VWAP": float(last_kline.get("VWAP", 0))
            }
            
            # Создаем событие для Redis Pub/Sub (его поймает API и WebSocket)
            event = CandleUpdateEvent(
                strategy_id=self.strategy_id,
                symbol=symbol,
                tf=interval,
                open=float(last_kline["open"]),
                high=float(last_kline["high"]),
                low=float(last_kline["low"]),
                close=float(last_kline["close"]),
                volume=float(last_kline["volume"]),
                indicators=indicators_data,
                timestamp=ts / 1000.0
            )
            
            # 2. Сохраняем в Redis List для мгновенного доступа фронтенда к истории последних свечей
            r_key = get_candles_key(self.strategy_id, symbol, interval)
            self.bus.redis.rpush(r_key, event.json())
            self.bus.redis.ltrim(r_key, -200, -1) # Храним только последние 200 свечей
            
            # 3. Публикуем событие в шину. На это событие реагирует агрегатор для проверки ордеров.
            self.bus.publish(CH_STRATEGY_EVENTS, event.dict())
            
        return df

    def update_working_symbols(self):
        """ Обновляет список символов и сохраняет метаданные в Redis. """
        try:
            logger.info("Обновление списка символов...")
            response = self.http.get_tickers(category="linear")
            if response.get("retCode") != 0:
                logger.error("Ошибка API при обновлении тикеров")
                return

            tickers = response.get("result", {}).get("list", [])
            tickers = [t for t in tickers if t.get("symbol", "").endswith("USDT")]
            tickers.sort(key=lambda x: abs(float(x.get("price24hPcnt", 0))), reverse=True)

            top_symbols = [t["symbol"] for t in tickers[:15]]

            active = set(self.positions.keys()) | set(self.active_orders.keys())
            self.working_symbols = set(top_symbols) | active
            
            # --- Сохранение метаданных в Redis ---
            meta = StrategyMetadata(
                strategy_id=self.strategy_id,
                name=STRATEGY_NAME,
                description="SuperTrend + Struktur Breakout Strategy",
                symbols=list(self.working_symbols),
                timeframes=[str(self.klines_interval)],
                indicators_config={
                    "rsi_period": self.rsi_period,
                    "st_multiplier": 2.5
                },
                custom_settings={
                    "risk_percent": self.risk_percent,
                    "leverage": self.leverage
                }
            )
            
            # Ключ: strategy:{id}:meta
            meta_key = get_meta_key(self.strategy_id)
            # Сохраняем как Hash (плоский словарь)
            meta_dict = meta.dict()
            # Превращаем сложные объекты в JSON для хранения в Hash
            for k, v in meta_dict.items():
                if isinstance(v, (list, dict)):
                    meta_dict[k] = json.dumps(v)
            
            self.bus.redis.hset(meta_key, mapping=meta_dict)
            
            logger.info(f"Активные символы ({len(self.working_symbols)}): {self.working_symbols}")

        except Exception as e:
            logger.error(f"Ошибка update_working_symbols: {e}")

    # -------------------------------------------------------------------------
    # Обработчики событий (Event Handlers)
    # -------------------------------------------------------------------------
    def handle_order_update(self, data: dict):
        """Обработка обновлений ордеров (унифицированное событие)."""
        try:
            event = OrderUpdateEvent(**data)
            symbol = event.symbol
            
            # Локальный учет ордеров
            if symbol not in self.active_orders:
                self.active_orders[symbol] = {}

            if event.status in ["New", "PartiallyFilled"]:
                # Сохраняем/обновляем
                self.active_orders[symbol][event.order_id] = event
            elif event.status in ["Filled", "Cancelled", "Rejected"]:
                # Удаляем
                if event.order_id in self.active_orders[symbol]:
                    del self.active_orders[symbol][event.order_id]
                if not self.active_orders[symbol]:
                    del self.active_orders[symbol]

            logger.info(f"Update ордера {event.order_id}: {event.status} {event.filled_qty}/{event.remaining_qty}")
        except Exception as e:
            logger.error(f"Ошибка handle_order_update: {e}")

    def handle_position_update(self, data: dict):
        """Обработка обновлений позиций."""
        try:
            event = PositionUpdateEvent(**data)
            # Обновляем локальный кеш
            if event.size == 0:
                if event.symbol in self.positions:
                    del self.positions[event.symbol]
            else:
                self.positions[event.symbol] = event.size
            
            logger.info(f"Позиция {event.symbol} обновлена: {event.size}")
        except Exception as e:
            logger.error(f"Ошибка handle_position_update: {e}")

    # Метода handle_order_filled больше нет, используется единый handle_order_update

    # -------------------------------------------------------------------------
    # Main Loop (Запуск)
    # -------------------------------------------------------------------------
    def start(self):
        """Запуск цикла стратегии."""
        logger.info(f"Запуск стратегии {self.strategy_id}")
        
        # Подписки
        if not self.test_mode:
            self.bus.subscribe("OrderUpdateEvent", self.handle_order_update)
            self.bus.subscribe("PositionUpdateEvent", self.handle_position_update)
            self.bus.start()

        self.update_working_symbols()

        while self.running:
            try:
                now = time.time()

                # Периодическое обновление списка символов (раз в час)
                if now - self.last_ticker_update > 3600:
                    self.update_working_symbols()
                    self.last_ticker_update = now

                # Анализ рынка (раз в минуту)
                if now - self.last_candle_update > 60:
                    for sym in list(self.working_symbols):
                        df = self.get_historical_data(sym)
                        if not df.empty:
                            self.check_entry_signals(df, sym)
                            self.check_exit_signals(df, sym)
                    self.last_candle_update = now

            except KeyboardInterrupt:
                logger.info("Остановка по Ctrl+C")
                self.running = False
            except Exception as e:
                logger.error(f"Исключение в основном цикле: {e}")
                time.sleep(5)
            
            time.sleep(1)
