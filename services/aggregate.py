import json
import time
import asyncio
import redis
import os
from datetime import datetime
from typing import Dict, Any, Optional

from events import (
    CH_STRATEGY_EVENTS, StrategySignalEvent, CandleUpdateEvent,
    OrderExecutionEvent, PositionStateEvent, TradeTerminalEvent,
    get_signals_ch
)
from storage import TradeStorage

class AggregateService:
    def __init__(self, redis_host='redis', db_path="trades.db"):
        self.r = redis.Redis(host=redis_host, port=6379, db=0, decode_responses=True)
        self.storage = TradeStorage(db_path)
        
        # In-memory state: positions[strategy_id][symbol]
        self.positions: Dict[str, Dict[str, Any]] = {}
        # In-memory state: orders[strategy_id][symbol] (Limit orders)
        self.orders: Dict[str, Dict[str, Any]] = {}

    async def run(self):
        pubsub = self.r.pubsub()
        pubsub.subscribe(CH_STRATEGY_EVENTS)
        print("Aggregate Service started, listening for events...")

        while True:
            try:
                message = pubsub.get_message(ignore_subscribe_messages=True)
                if message:
                    data = json.loads(message['data'])
                    await self.handle_event(data)
                
                await asyncio.sleep(0.01)
            except Exception as e:
                print(f"Error in aggregate loop: {e}")
                await asyncio.sleep(1)

    async def handle_event(self, data: dict):
        event_type = data.get('event_type')
        
        if event_type == "StrategySignalEvent":
            await self.process_signal(data)
        elif event_type == "CandleUpdateEvent":
            await self.process_candle(data)
        elif event_type == "StrategySetTPSLEvent":
            await self.update_tp_sl(data)

    async def process_signal(self, data: dict):
        strategy_id = data['strategy_id']
        symbol = data['symbol']
        action = data['action']
        price = data.get('price') # Limit price if provided
        
        print(f"Signal received: {strategy_id} {symbol} {action} @ {price}")

        if action.startswith("OPEN"):
            if not price: # Market order
                # For simulation, we'll fill at some "current" price. 
                # Real fill happens on next candle, but let's assume we have a price or wait for candle.
                # To keep it simple, we store it as a pending order if price is missing, 
                # but we'll fill it immediately on the next candle's Open.
                self._add_order(strategy_id, symbol, data, "MARKET")
            else:
                self._add_order(strategy_id, symbol, data, "LIMIT")
                
        elif action.startswith("CLOSE"):
            pos = self._get_position(strategy_id, symbol)
            if pos:
                # Market close
                await self.close_position(strategy_id, symbol, pos, price_override=None, reason="SIGNAL")

    async def process_candle(self, data: dict):
        strategy_id = data['strategy_id']
        symbol = data['symbol']
        high = data['high']
        low = data['low']
        close = data['close']
        timestamp = data['timestamp']

        # 1. Check pending orders
        order = self._get_order(strategy_id, symbol)
        if order:
            await self.check_order_fill(strategy_id, symbol, order, data)

        # 2. Check open positions (TP/SL)
        pos = self._get_position(strategy_id, symbol)
        if pos:
            await self.check_position_exit(strategy_id, symbol, pos, data)

    async def check_order_fill(self, strategy_id: str, symbol: str, order: dict, candle: dict):
        price = order.get('price')
        filled = False
        fill_price = price

        if order['order_type'] == "MARKET":
            filled = True
            fill_price = candle['open']
        else: # LIMIT
            if candle['low'] <= price <= candle['high']:
                filled = True

        if filled:
            print(f"Order FILLED: {strategy_id} {symbol} at {fill_price}")
            # Create Position
            side = "LONG" if order['action'] == "OPEN_LONG" else "SHORT"
            new_pos = {
                "strategy_id": strategy_id,
                "symbol": symbol,
                "side": side,
                "size": 1.0, # Simplified
                "entry_price": fill_price,
                "entry_time": candle['timestamp'],
                "stop_loss": order.get('stop_loss'),
                "take_profit": order.get('take_profit'),
                "unrealised_pnl": 0.0
            }
            self.positions.setdefault(strategy_id, {})[symbol] = new_pos
            self.orders[strategy_id].pop(symbol)

            # Notify
            event = OrderExecutionEvent(
                strategy_id=strategy_id,
                symbol=symbol,
                order_id=order['event_id'],
                order_type=order['order_type'],
                side="BUY" if side == "LONG" else "SELL",
                price=fill_price,
                qty=1.0,
                status="FILLED"
            )
            self._publish_event(event)
            
            # Save to SQLite
            self.storage.save_order({
                "order_id": order['event_id'],
                "strategy_id": strategy_id,
                "symbol": symbol,
                "side": order['action'],
                "price": fill_price,
                "qty": 1.0,
                "type": order['order_type'],
                "status": "FILLED"
            })

            # Sync to Redis
            self._sync_state_to_redis(strategy_id, symbol, "orders", None, remove=True)
            self._sync_state_to_redis(strategy_id, symbol, "positions", new_pos)

    async def check_position_exit(self, strategy_id: str, symbol: str, pos: dict, candle: dict):
        sl = pos.get('stop_loss')
        tp = pos.get('take_profit')
        side = pos['side']
        exit_price = None
        reason = None

        if side == "LONG":
            if sl and candle['low'] <= sl:
                exit_price = sl
                reason = "SL"
            elif tp and candle['high'] >= tp:
                exit_price = tp
                reason = "TP"
        else: # SHORT
            if sl and candle['high'] >= sl:
                exit_price = sl
                reason = "SL"
            elif tp and candle['low'] <= tp:
                exit_price = tp
                reason = "TP"

        if exit_price:
            await self.close_position(strategy_id, symbol, pos, exit_price, reason, candle['timestamp'])

    async def close_position(self, strategy_id: str, symbol: str, pos: dict, price_override: Optional[float], reason: str, timestamp: float = None):
        exit_price = price_override or pos.get('last_close', pos['entry_price'])
        timestamp = timestamp or time.time()
        
        # Calculate PnL
        if pos['side'] == "LONG":
            pnl = (exit_price - pos['entry_price']) * pos['size']
        else:
            pnl = (pos['entry_price'] - exit_price) * pos['size']

        print(f"Position CLOSED: {strategy_id} {symbol} {reason} at {exit_price} PnL: {pnl}")

        # Update Storage
        self.storage.save_trade({
            "strategy_id": strategy_id,
            "symbol": symbol,
            "side": pos['side'],
            "entry_price": pos['entry_price'],
            "exit_price": exit_price,
            "qty": pos['size'],
            "pnl": pnl,
            "entry_time": pos['entry_time'],
            "exit_time": timestamp,
            "metadata": {"reason": reason}
        })

        # Remove position
        self.positions[strategy_id].pop(symbol)
        self._sync_state_to_redis(strategy_id, symbol, "positions", None, remove=True)

        # Notify
        event = TradeTerminalEvent(
            strategy_id=strategy_id,
            symbol=symbol,
            trigger_type=reason if reason in ["TP", "SL"] else "TP", # Field expects TP/SL literal
            exit_price=exit_price,
            pnl=pnl,
            realised_pnl=pnl
        )
        self._publish_event(event)
        
        # Also broadcast position update (FLAT)
        update_event = PositionStateEvent(
            strategy_id=strategy_id,
            symbol=symbol,
            side="FLAT",
            size=0,
            entry_price=0,
            unrealised_pnl=0
        )
        self._publish_event(update_event)

    async def update_tp_sl(self, data: dict):
        strategy_id = data['strategy_id']
        symbol = data['symbol']
        pos = self._get_position(strategy_id, symbol)
        if pos:
            if 'stop_loss' in data: pos['stop_loss'] = data['stop_loss']
            if 'take_profit' in data: pos['take_profit'] = data['take_profit']
            
            # Notify UI
            event = PositionStateEvent(
                strategy_id=strategy_id,
                symbol=symbol,
                side=pos['side'],
                size=pos['size'],
                entry_price=pos['entry_price'],
                stop_loss=pos['stop_loss'],
                take_profit=pos['take_profit']
            )
            self._publish_event(event)
            # Sync to Redis
            self._sync_state_to_redis(strategy_id, symbol, "positions", pos)

    def _add_order(self, strategy_id: str, symbol: str, data: dict, order_type: str):
        if strategy_id not in self.orders:
            self.orders[strategy_id] = {}
        data['order_type'] = order_type
        self.orders[strategy_id][symbol] = data
        self._sync_state_to_redis(strategy_id, symbol, "orders", data)

    def _get_order(self, strategy_id: str, symbol: str) -> Optional[dict]:
        return self.orders.get(strategy_id, {}).get(symbol)

    def _get_position(self, strategy_id: str, symbol: str) -> Optional[dict]:
        return self.positions.get(strategy_id, {}).get(symbol)

    def _publish_event(self, event: Any):
        self.r.publish(CH_STRATEGY_EVENTS, event.json())

    def _sync_state_to_redis(self, strategy_id: str, symbol: str, state_type: str, data: Any, remove: bool = False):
        """
        state_type: 'positions' or 'orders'
        """
        key = f"strategy:{strategy_id}:{state_type}"
        if remove:
            self.r.hdel(key, symbol)
        else:
            self.r.hset(key, symbol, json.dumps(data))

if __name__ == "__main__":
    redis_host = os.getenv('REDIS_HOST', 'redis')
    db_path = os.getenv("DB_PATH", "trades.db")
    service = AggregateService(redis_host=redis_host, db_path=db_path)
    asyncio.run(service.run())
