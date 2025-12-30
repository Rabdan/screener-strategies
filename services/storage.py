import sqlite3
import json
from datetime import datetime
from typing import List, Optional
import os

class TradeStorage:
    def __init__(self, db_path: str = "trades.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_id TEXT,
                    symbol TEXT,
                    side TEXT,
                    entry_price REAL,
                    exit_price REAL,
                    qty REAL,
                    pnl REAL,
                    entry_time TIMESTAMP,
                    exit_time TIMESTAMP,
                    metadata TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    order_id TEXT PRIMARY KEY,
                    strategy_id TEXT,
                    symbol TEXT,
                    side TEXT,
                    price REAL,
                    qty REAL,
                    type TEXT,
                    status TEXT,
                    created_at TIMESTAMP
                )
            """)

    def save_trade(self, trade_data: dict):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO trades (strategy_id, symbol, side, entry_price, exit_price, qty, pnl, entry_time, exit_time, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade_data['strategy_id'],
                trade_data['symbol'],
                trade_data['side'],
                trade_data['entry_price'],
                trade_data.get('exit_price'),
                trade_data['qty'],
                trade_data.get('pnl'),
                trade_data['entry_time'],
                trade_data.get('exit_time'),
                json.dumps(trade_data.get('metadata', {}))
            ))

    def save_order(self, order_data: dict):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO orders (order_id, strategy_id, symbol, side, price, qty, type, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order_data['order_id'],
                order_data['strategy_id'],
                order_data['symbol'],
                order_data['side'],
                order_data['price'],
                order_data['qty'],
                order_data['type'],
                order_data['status'],
                order_data.get('created_at', datetime.now().isoformat())
            ))

    def get_trades(self, strategy_id: str, symbol: Optional[str] = None) -> List[dict]:
        query = "SELECT * FROM trades WHERE strategy_id = ?"
        params = [strategy_id]
        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]
