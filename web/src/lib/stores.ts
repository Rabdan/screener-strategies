import { writable, get } from 'svelte/store';

export type StrategyState = 'waiting' | 'in_trade';

export interface Strategy {
    id: string;
    name: string;
    description?: string;
    activeInstruments: number;
    pnl: number;
    indicators?: Record<string, Record<string, IndicatorConfig>>;
}

export interface IndicatorConfig {
    label: string;
    color: string;
    linestyle?: '-' | '--' | ':' | 'solid' | 'dashed' | 'dotted';
    marker?: '^' | 'v' | 'circle';
    value?: number; // For horizontal lines
}

export interface Instrument {
    symbol: string;
    lastPrice: number;
    strategies: Array<{
        strategyId: string;
        strategyName: string;
        status: 'WAIT' | 'PENDING' | 'INTRADE' | 'UPDATE';
    }>;
}

export interface Candle {
    time: number;
    open: number;
    high: number;
    low: number;
    close: number;
    volume?: number;
    indicators?: Record<string, number>;
}

export interface Trade {
    time: number;
    position: 'belowBar' | 'aboveBar';
    color: string;
    shape: 'arrowUp' | 'arrowDown' | 'circle';
    text: string;
}

export function getPricePrecision(price: number): number {
    if (!price) return 2;
    if (price < 0.001) return 8;
    if (price < 0.1) return 6;
    if (price < 1) return 4;
    return 2;
}

// --- Демо-данные / Заглушки ---
const DUMMY_STRATEGIES = [
    {
        strategy_id: 'top_trend_breakout',
        name: 'Пробой тренда',
        description: 'Мониторинг установившихся трендов для поиска высоковероятных пробоев с подтверждением объема и импульса RSI.',
        symbols: ['BTCUSDT', 'ETHUSDT'],
        indicators: {
            "main": {
                "st_trend": { color: "yellow", linestyle: "-", label: "ST Trend" },
                "highex": { color: "blue", marker: "^", label: "High Ex" },
                "lowex": { color: "orange", marker: "v", label: "Low Ex" },
            },
            "volume_pane": {
                "volume": { color: "gray", linestyle: "histogram", label: "Volume" },
                "volsma": { color: "red", linestyle: "-", label: "Vol SMA" },
            },
            "natr_pane": {
                "natr": { color: "red", linestyle: "-", label: "NATR" },
            },
            "stochrsi_pane": {
                "stochk": { color: "green", linestyle: "-", label: "Stoch K" },
                "stochd": { color: "red", linestyle: "--", label: "Stoch D" },
                "stochrsi_overbought": { value: 80, color: "rgba(0,0,0,0.5)", linestyle: ":", label: "Overbought" },
                "stochrsi_oversold": { value: 20, color: "rgba(0,0,0,0.5)", linestyle: ":", label: "Oversold" },
            }
        }
    },
    {
        strategy_id: 'rsi_reversal',
        name: 'Разворот RSI',
        description: 'Контртрендовая стратегия, выявляющая условия перепроданности/перекупленности на основных ликвидных парах.',
        symbols: ['SOLUSDT', 'ARBUSDT'],
        indicators: {
            "main": {},
            "stochRSI": {
                "rsi": { color: "#6366f1", label: "RSI" },
                "rsi_70": { value: 70, color: "rgba(239, 68, 68, 0.5)", linestyle: ":", label: "70" },
                "rsi_30": { value: 30, color: "rgba(16, 185, 129, 0.5)", linestyle: ":", label: "30" }
            }
        }
    },
    {
        strategy_id: 'ema_cross',
        name: 'Пересечение EMA 50/200',
        description: 'Классическая трендовая стратегия, использующая пересечение экспоненциальных скользящих средних.',
        symbols: ['BTCUSDT', 'BNBUSDT'],
        indicators: {
            "main": {
                "ema_50": { color: "#3b82f6", label: "EMA 50" },
                "ema_200": { color: "#ef4444", label: "EMA 200" }
            }
        }
    }
];

const DUMMY_INSTRUMENTS = [
    {
        symbol: 'BTCUSDT', last_price: 65432.10, strategies: [
            { strategyId: 'top_trend_breakout', strategyName: 'Пробой тренда', status: 'INTRADE' },
            { strategyId: 'ema_cross', strategyName: 'Пересечение EMA 50/200', status: 'WAIT' }
        ]
    },
    {
        symbol: 'ETHUSDT', last_price: 3456.78, strategies: [
            { strategyId: 'top_trend_breakout', strategyName: 'Пробой тренда', status: 'PENDING' }
        ]
    },
    {
        symbol: 'SOLUSDT', last_price: 145.20, strategies: [
            { strategyId: 'rsi_reversal', strategyName: 'Разворот RSI', status: 'UPDATE' }
        ]
    },
    {
        symbol: 'BNBUSDT', last_price: 580.45, strategies: [
            { strategyId: 'ema_cross', strategyName: 'Пересечение EMA 50/200', status: 'WAIT' }
        ]
    },
    {
        symbol: 'ADAUSDT', last_price: 0.4521, strategies: [
            { strategyId: 'rsi_reversal', strategyName: 'Разворот RSI', status: 'WAIT' }
        ]
    },
    {
        symbol: 'XRPUSDT', last_price: 0.6120, strategies: [
            { strategyId: 'top_trend_breakout', strategyName: 'Пробой тренда', status: 'WAIT' },
            { strategyId: 'rsi_reversal', strategyName: 'Разворот RSI', status: 'INTRADE' }
        ]
    },
    {
        symbol: 'DOTUSDT', last_price: 7.24, strategies: [
            { strategyId: 'ema_cross', strategyName: 'Пересечение EMA 50/200', status: 'PENDING' }
        ]
    },
    {
        symbol: 'LINKUSDT', last_price: 18.15, strategies: [
            { strategyId: 'top_trend_breakout', strategyName: 'Пробой тренда', status: 'UPDATE' }
        ]
    },
    {
        symbol: 'AVAXUSDT', last_price: 35.60, strategies: [
            { strategyId: 'rsi_reversal', strategyName: 'Разворот RSI', status: 'WAIT' }
        ]
    },
    {
        symbol: 'MATICUSDT', last_price: 0.72, strategies: [
            { strategyId: 'ema_cross', strategyName: 'Пересечение EMA 50/200', status: 'INTRADE' }
        ]
    },
    {
        symbol: 'ATOMUSDT', last_price: 8.45, strategies: [
            { strategyId: 'top_trend_breakout', strategyName: 'Пробой тренда', status: 'WAIT' }
        ]
    },
    {
        symbol: 'LTCUSDT', last_price: 82.30, strategies: [
            { strategyId: 'rsi_reversal', strategyName: 'Разворот RSI', status: 'PENDING' }
        ]
    },
    {
        symbol: 'NEARUSDT', last_price: 6.80, strategies: [
            { strategyId: 'top_trend_breakout', strategyName: 'Пробой тренда', status: 'INTRADE' }
        ]
    },
    {
        symbol: 'OPUSDT', last_price: 2.45, strategies: [
            { strategyId: 'ema_cross', strategyName: 'Пересечение EMA 50/200', status: 'UPDATE' }
        ]
    },
    {
        symbol: 'ARBUSDT', last_price: 1.15, strategies: [
            { strategyId: 'rsi_reversal', strategyName: 'Разворот RSI', status: 'WAIT' }
        ]
    },
    {
        symbol: 'INJUSDT', last_price: 28.50, strategies: [
            { strategyId: 'top_trend_breakout', strategyName: 'Пробой тренда', status: 'WAIT' }
        ]
    },
    {
        symbol: 'TIAUSDT', last_price: 11.20, strategies: [
            { strategyId: 'ema_cross', strategyName: 'Пересечение EMA 50/200', status: 'PENDING' }
        ]
    },
    {
        symbol: 'RNDRUSDT', last_price: 9.40, strategies: [
            { strategyId: 'rsi_reversal', strategyName: 'Разворот RSI', status: 'INTRADE' }
        ]
    },
    {
        symbol: 'JUPUSDT', last_price: 1.05, strategies: [
            { strategyId: 'top_trend_breakout', strategyName: 'Пробой тренда', status: 'WAIT' }
        ]
    },
    {
        symbol: 'PYTHUSDT', last_price: 0.58, strategies: [
            { strategyId: 'ema_cross', strategyName: 'Пересечение EMA 50/200', status: 'UPDATE' }
        ]
    }
];

function generateDummyCandles() {
    const candles = [];
    const now = Math.floor(Date.now() / 1000);
    let lastClose = 50000;
    let rsi = 50;
    let sma = 50000;

    for (let i = 500; i >= 0; i--) {
        const open = lastClose;
        const close = open + (Math.random() - 0.5) * 500;
        const high = Math.max(open, close) + Math.random() * 100;
        const low = Math.min(open, close) - Math.random() * 100;

        // Mock indicators
        rsi = Math.max(10, Math.min(90, rsi + (Math.random() - 0.5) * 10));
        sma = sma * 0.95 + close * 0.05;
        const trend = i % 50 > 25 ? high + 100 : low - 100;

        candles.push({
            timestamp: now - i * 3600,
            open, high, low, close,
            volume: 10 + Math.random() * 90,
            indicators: {
                st_trend: trend,
                highex: i % 40 === 0 ? high + 50 : undefined,
                lowex: i % 45 === 0 ? low - 50 : undefined,
                volsma: 40 + Math.random() * 20,
                natr: 1 + Math.random(),
                stochk: rsi,
                stochd: rsi * 0.9 + 5,
                rsi: rsi,
                ema50: sma * 1.2,
                ema200: sma * 0.9 + close * 0.1,
            } as any
        });
        lastClose = close;
    }
    return candles;
}

// --- Сторы ---
export const strategies = writable<Strategy[]>([]);
export const activeStrategyId = writable<string | null>('top_trend_breakout');
export const activeStrategyDetail = writable<Strategy | null>(null);
export const instruments = writable<Instrument[]>([]);
export const selectedInstrument = writable<string | null>(null);
export const viewMode = writable<'watchlist' | 'chart'>('watchlist');
export const showMobileSidebar = writable<boolean>(false);
export const desktopInspectorOpen = writable<boolean>(true);

const API_URL = 'http://localhost:8000';
const WS_URL = 'ws://localhost:8000';

let socket: WebSocket | null = null;

// --- Помощник для маппинга данных ---
function mapStrategy(s: any): Strategy {
    return {
        id: s.strategy_id,
        name: s.name || s.strategy_id,
        description: s.description || 'Динамическая стратегия, отслеживающая волатильность монет и структуру тренда.',
        activeInstruments: s.symbols?.length || 0,
        pnl: Math.random() * 500 - 100, // Фиктивный PnL для демо
        indicators: s.indicators || []
    };
}

// --- API Функции ---
export async function fetchStrategies() {
    let mapped: Strategy[] = [];
    try {
        const response = await fetch(`${API_URL}/strategies`);
        const data = await response.json();
        mapped = data.length > 0 ? data.map(mapStrategy) : DUMMY_STRATEGIES.map(mapStrategy);
    } catch (e) {
        console.warn("API Offline: Используются демо-стратегии");
        mapped = DUMMY_STRATEGIES.map(mapStrategy);
    }

    strategies.set(mapped);

    // Синхронизация активной детали
    const currentId = get(activeStrategyId);
    const detail = mapped.find(i => i.id === currentId);
    if (detail) {
        activeStrategyDetail.set(detail);
    } else if (mapped.length > 0) {
        activeStrategyId.set(mapped[0].id);
        activeStrategyDetail.set(mapped[0]);
    }
}

export async function fetchInstruments() {
    try {
        const response = await fetch(`${API_URL}/instruments`);
        if (!response.ok) throw new Error();
        const data = await response.json();
        instruments.set(data.map((i: any) => ({
            symbol: i.symbol,
            lastPrice: i.last_price || 0,
            strategies: i.strategies || []
        })));
    } catch (e) {
        console.warn("API Offline: Используются демо-инструменты");
        instruments.set(DUMMY_INSTRUMENTS.map(i => ({
            symbol: i.symbol,
            lastPrice: i.last_price,
            strategies: i.strategies as any
        })));
    }
}

export async function fetchCandles(strategyId: string, symbol: string) {
    try {
        const response = await fetch(`${API_URL}/strategies/${strategyId}/candles/${symbol}/1h`);
        if (!response.ok) return generateDummyCandles();
        return await response.json();
    } catch (e) {
        return generateDummyCandles();
    }
}

export async function fetchTrades(strategyId: string, symbol: string) {
    try {
        const response = await fetch(`${API_URL}/strategies/${strategyId}/trades?symbol=${symbol}`);
        if (!response.ok) throw new Error();
        return await response.json();
    } catch (e) {
        // Возврат демо-сделок
        const now = Math.floor(Date.now() / 1000);
        return [
            { entry_time: now - 86400, exit_time: now - 82800, side: 'LONG', pnl: 45.20 },
            { entry_time: now - 172800, exit_time: now - 169200, side: 'SHORT', pnl: -12.50 }
        ];
    }
}

export async function fetchInstrumentState(strategyId: string, symbol: string) {
    try {
        const response = await fetch(`${API_URL}/strategies/${strategyId}/state/${symbol}`);
        if (!response.ok) throw new Error();
        return await response.json();
    } catch (e) {
        // Возврат демо-состояния
        return {
            position: {
                symbol,
                side: 'LONG',
                entry_price: 64120.50,
                take_profit: 67000.00,
                stop_loss: 62500.00,
                unrealised_pnl: 145.20
            },
            order: null
        };
    }
}

export function initWebSocket(strategyId: string) {
    if (socket) socket.close();
    try {
        socket = new WebSocket(`${WS_URL}/ws/${strategyId}`);
        socket.onmessage = (event) => {
            const msg = JSON.parse(event.data);
            if (msg.type === 'watchlist_ping') {
                instruments.update(items => items.map(i =>
                    i.symbol === msg.symbol ? { ...i, lastPrice: msg.price } : i
                ));
            } else if (msg.type === 'update') {
                fetchInstruments();
                window.dispatchEvent(new CustomEvent('ws_message', { detail: msg }));
            } else if (msg.type === 'candle_update') {
                window.dispatchEvent(new CustomEvent('ws_message', { detail: msg }));
            }
        };
    } catch (e) {
        console.warn("Ошибка подключения WebSocket (API вероятно оффлайн)");
    }
}

export function selectCoinStrategy(symbol: string, strategyId: string) {
    selectedInstrument.set(symbol);
    activeStrategyId.set(strategyId);
    viewMode.set('chart');
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ action: 'select_symbol', symbol }));
    }
}

export function showWatchlist() {
    viewMode.set('watchlist');
    selectedInstrument.set(null);
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ action: 'select_symbol', symbol: null }));
    }
}
