from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import redis
import json
import asyncio
import os
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from events import (
    get_meta_key, get_candles_key, CH_STRATEGY_EVENTS,
    StrategyMetadata, CandleUpdateEvent
)
from storage import TradeStorage

app = FastAPI(title="Crypto Strategy API")

# CORS for SvelteKit
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redis & Storage
r = redis.Redis(host=os.getenv('REDIS_HOST', 'redis'), port=6379, db=0, decode_responses=True)
db_path = os.getenv("DB_PATH", "trades.db")
storage = TradeStorage(db_path)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.subscriptions: Dict[WebSocket, str] = {} # WebSocket -> current selected symbol

    async def connect(self, websocket: WebSocket, strategy_id: str):
        await websocket.accept()
        if strategy_id not in self.active_connections:
            self.active_connections[strategy_id] = []
        self.active_connections[strategy_id].append(websocket)

    def disconnect(self, websocket: WebSocket, strategy_id: str):
        if strategy_id in self.active_connections:
            self.active_connections[strategy_id].remove(websocket)
        if websocket in self.subscriptions:
            del self.subscriptions[websocket]

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)

    async def broadcast_strategy(self, strategy_id: str, message: dict):
        if strategy_id in self.active_connections:
            for connection in self.active_connections[strategy_id]:
                await connection.send_json(message)

    async def broadcast_all(self, message: dict):
        for strategy_id in self.active_connections:
            for connection in self.active_connections[strategy_id]:
                try:
                    await connection.send_json(message)
                except:
                    pass

manager = ConnectionManager()

# --- REST ENDPOINTS ---

@app.get("/strategies")
def list_strategies():
    keys = r.keys("strategy:*:meta")
    strategies = []
    for key in keys:
        meta = r.hgetall(key)
        if meta:
            # Parse bit-encoded/json fields
            for field in ['symbols', 'timeframes', 'indicators_config', 'custom_settings']:
                if field in meta:
                    try:
                        meta[field] = json.loads(meta[field])
                    except:
                        pass
            strategies.append(meta)
    return strategies

@app.get("/instruments")
def list_instruments():
    # 1. Get all strategies and their metadata
    strategy_keys = r.keys("strategy:*:meta")
    strategies_meta = {}
    for key in strategy_keys:
        sid = key.split(":")[1]
        meta = r.hgetall(key)
        try:
            meta['symbols'] = json.loads(meta.get('symbols', '[]'))
        except:
            meta['symbols'] = []
        strategies_meta[sid] = meta

    # 2. Consolidate symbols
    instruments_map = {}
    for sid, meta in strategies_meta.items():
        symbols = meta.get('symbols', [])
        
        # Get currently active state for this strategy
        strategy_orders = r.hgetall(f"strategy:{sid}:orders")
        strategy_positions = r.hgetall(f"strategy:{sid}:positions")

        for sym in symbols:
            if sym not in instruments_map:
                # Try to get last price from the first available strategy's candle history
                last_price = 0.0
                tfs = meta.get('timeframes', [])
                if tfs:
                    c_key = get_candles_key(sid, sym, tfs[0])
                    last_c = r.lindex(c_key, -1)
                    if last_c:
                        try:
                            last_price = json.loads(last_c).get('close', 0.0)
                        except:
                            pass

                instruments_map[sym] = {
                    "symbol": sym,
                    "last_price": last_price,
                    "strategies": []
                }
            
            # Determine status
            status = "WAIT"
            if sym in strategy_positions:
                status = "INTRADE"
            elif sym in strategy_orders:
                status = "PENDING"
            
            instruments_map[sym]["strategies"].append({
                "strategy_id": sid,
                "strategy_name": meta.get("name", sid),
                "status": status
            })

    return list(instruments_map.values())

@app.get("/strategies/{strategy_id}/candles/{symbol}/{tf}")
def get_historical_candles(strategy_id: str, symbol: str, tf: str, limit: int = 100):
    key = get_candles_key(strategy_id, symbol, tf)
    # Candles are stored as a list of JSON strings in Redis
    candles_raw = r.lrange(key, -limit, -1)
    return [json.loads(c) for c in candles_raw]

@app.get("/strategies/{strategy_id}/trades")
def get_trades(strategy_id: str, symbol: Optional[str] = None):
    return storage.get_trades(strategy_id, symbol)

@app.get("/strategies/{strategy_id}/state/{symbol}")
def get_instrument_state(strategy_id: str, symbol: str):
    """
    Returns current position and pending order for a specific symbol in a strategy
    """
    pos = r.hget(f"strategy:{strategy_id}:positions", symbol)
    order = r.hget(f"strategy:{strategy_id}:orders", symbol)
    
    return {
        "position": json.loads(pos) if pos else None,
        "order": json.loads(order) if order else None
    }

# --- WEBSOCKET ---

async def redis_listener():
    pubsub = r.pubsub()
    pubsub.subscribe(CH_STRATEGY_EVENTS)
    
    while True:
        try:
            message = pubsub.get_message(ignore_subscribe_messages=True)
            if message:
                data = json.loads(message['data'])
                event_type = data.get('event_type')
                strategy_id = data.get('strategy_id')
                
                if event_type == "CandleUpdateEvent":
                    symbol = data.get('symbol')
                    # Отправляем цену во все вачлисты
                    await broadcast_watchlist_ping(symbol, data)
                    # Отправляем полную свечу только подписанным на график
                    await notify_candle_update(strategy_id, symbol, data)
                
                elif event_type in ["OrderExecutionEvent", "PositionStateEvent", "TradeTerminalEvent"]:
                    # Глобальное обновление для всех клиентов (обновить статусы)
                    await manager.broadcast_all({
                        "type": "update",
                        "event": event_type,
                        "data": data
                    })

            await asyncio.sleep(0.01)
        except Exception as e:
            print(f"Redis listener error: {e}")
            await asyncio.sleep(1)

async def broadcast_watchlist_ping(symbol: str, data: dict):
    ping = {
        "type": "watchlist_ping",
        "symbol": symbol,
        "price": data.get('close'),
        "timestamp": data.get('timestamp')
    }
    await manager.broadcast_all(ping)

async def notify_candle_update(strategy_id: str, symbol: str, data: dict):
    if strategy_id not in manager.active_connections:
        return
        
    for ws in manager.active_connections[strategy_id]:
        if manager.subscriptions.get(ws) == symbol:
            await ws.send_json({
                "type": "candle_update",
                "strategy_id": strategy_id,
                "symbol": symbol,
                "data": data
            })

@app.websocket("/ws/{strategy_id}")
async def websocket_endpoint(websocket: WebSocket, strategy_id: str):
    await manager.connect(websocket, strategy_id)
    try:
        while True:
            # Receive commands from front-end (e.g., "select_symbol")
            data = await websocket.receive_json()
            if data.get("action") == "select_symbol":
                symbol = data.get("symbol")
                manager.subscriptions[websocket] = symbol
                print(f"Client subscribed to {symbol} in strategy {strategy_id}")
    except WebSocketDisconnect:
        manager.disconnect(websocket, strategy_id)
    except Exception as e:
        print(f"WS Error: {e}")
        manager.disconnect(websocket, strategy_id)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(redis_listener())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
