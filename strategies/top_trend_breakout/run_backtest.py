import sys
import os
import logging
from main import TopTrendBreakOut
from backtest.backtester import Backtester

# Настройка путей
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

# Логирование
logging.basicConfig(level=logging.INFO)

def run_backtest():
    symbol = "PEOPLEUSDT"
    
    # Инициализация стратегии
    strategy = TopTrendBreakOut(test_mode=True, symbol=symbol)
    
    # Получение исторических данных
    print("Fetching historical data...")
    df = strategy.get_historical_data(symbol, limit=500)
    
    if df.empty:
        print("No data fetched.")
        return

    print(f"Fetched {len(df)} candles.")

    # Инициализация бектестера
    backtester = Backtester(strategy, symbol)
    
    # Запуск
    df_results, trades = backtester.run(df)
    
    # Результаты
    print(f"\nTotal Trades: {len(trades)}")
    if trades:
        total_pnl = sum(t.get('pnl', 0) for t in trades if t['type'] == 'Exit')
        print(f"Total PnL: {total_pnl:.2f}")
        print("Last 5 trades:")
        for t in trades[-5:]:
            print(t)
            
    # Визуализация
    backtester.plot_results(df_results)

if __name__ == "__main__":
    run_backtest()
