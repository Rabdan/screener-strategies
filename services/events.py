import time
import uuid
import json
from typing import Literal, Optional, List, Dict, Any

from pydantic import BaseModel, Field  # pyright: ignore[reportMissingImports]


class BaseEvent(BaseModel):
    """Базовый класс для всех событий системы."""

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = Field(default_factory=time.time)
    event_type: str = Field(default="")
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.event_type:
             self.event_type = self.__class__.__name__


"""
REDIS KEY PATTERNS & CHANNELS:
"""
CH_STRATEGY_EVENTS = "strategy:events"  # General Pub/Sub channel

def get_meta_key(strategy_id: str) -> str:
    return f"strategy:{strategy_id}:meta"

def get_candles_key(strategy_id: str, symbol: str, tf: str) -> str:
    return f"strategy:{strategy_id}:candles:{symbol}:{tf}"

def get_signals_ch(strategy_id: str) -> str:
    return f"strategy:{strategy_id}:signals"

class StrategyMetadata(BaseModel):
    """
    Метаданные стратегии для хранения в Redis (Hash).
    Key: strategy:{strategy_id}:meta
    """
    strategy_id: str
    name: str
    description: Optional[str] = None
    symbols: List[str] = []
    timeframes: List[str] = []
    indicators_config: Dict[str, Any] = {}
    custom_settings: Dict[str, Any] = {}
    is_active: bool = True


class CandleUpdateEvent(BaseEvent):
    """
    Обновление свечи и индикаторов.
    Key: strategy:{strategy_id}:candles:{symbol}:{tf}
    """
    strategy_id: str
    symbol: str
    tf: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    indicators: Dict[str, float] = {}  # Значения индикаторов для этой свечи


"""События стратегии (Prefix: StrategyEvent)"""


class StrategyLifecycleEvent(BaseEvent):
    """Событие управления жизненным циклом стратегии (старт/стоп)."""
    action: str # START, SHUTDOWN
    strategy_id: str


class StrategySignalEvent(BaseEvent):
    """
    Сигнал от Стратегии к ExecutionManager.
    Открытие/Закрытие позиции.
    """
    strategy_id: str
    symbol: str
    action: Literal['OPEN_LONG', 'OPEN_SHORT', 'CLOSE_LONG', 'CLOSE_SHORT']
    risk_pct: Optional[float] = None  # Для входа
    close_percent: Optional[float] = None  # 1.0 = 100%
    price: Optional[float] = None  # Limit price
    leverage: float = 1.0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None


class StrategySetTPSLEvent(BaseEvent):
    """Запрос на обновление TP/SL."""
    strategy_id: str
    symbol: str
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None


"""События Агрегатора / Эмулятора Биржи (Prefix: ExchangeEvent)"""


class ExchangeEvent(BaseEvent):
    """Базовый класс для событий эмуляции биржи."""
    strategy_id: str
    symbol: str


class OrderExecutionEvent(ExchangeEvent):
    """Событие срабатывания лимитного ордера или входа в позицию."""
    order_id: str
    order_type: Literal['LIMIT', 'MARKET']
    side: Literal['BUY', 'SELL']
    price: float
    qty: float
    status: Literal['FILLED', 'PARTIALLY_FILLED', 'CANCELLED']


class PositionStateEvent(ExchangeEvent):
    """Событие открытия/изменения позиции (эмуляция биржи)."""
    side: Literal['LONG', 'SHORT', 'FLAT']
    size: float
    entry_price: float
    unrealised_pnl: float = 0.0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None


class TradeTerminalEvent(ExchangeEvent):
    """Событие закрытия по TP или SL."""
    trigger_type: Literal['TP', 'SL']
    exit_price: float
    pnl: float
    realised_pnl: float


"""Информационные события (Legacy / Compatibility)"""


class OrderUpdateEvent(BaseEvent):
    """Старое событие обновления ордера (для совместимости)."""
    order_id: str
    symbol: str
    status: str
    price: Optional[float] = None


class PositionUpdateEvent(BaseEvent):
    """Старое событие обновления позиции."""
    symbol: str
    size: float
    entry_price: float
    unrealised_pnl: float = 0.0
