"""
Модуль расчета технических индикаторов для стратегии.
Содержит специфические реализации Heiken Ashi StochRSI и логику поиска экстремумов.
"""
from typing import Any, List, Tuple

import numpy as np
import pandas as pd
import pandas_ta as ta


class Indicators:
    """
    Класс-утилита для расчета индикаторов.
    """
    def __init__(self, rsi_period: int = 14):
        self.rsi_period = rsi_period

    def _heiken_stochrsi(
        self,
        data_df: pd.DataFrame,
        period_rsi: int = 14,
        smoothK: int = 3,
        smoothD: int = 3,
    ) -> Tuple[pd.Series, pd.Series]:
        """
        Рассчитывает Stochastic RSI на основе свечей Heiken Ashi.
        
        Алгоритм:
        1. Рассчитать свечи Heiken Ashi (HA).
        2. Взять HA Close и рассчитать RSI.
        3. Рассчитать StochRSI от полученного RSI.
        
        Возвращает:
            Tuple[pd.Series, pd.Series]: (StochK, StochD) в диапазоне 0-100.
        """
        heiken_ashi = pd.DataFrame(index=data_df.index)
        heiken_ashi["close"] = (
            data_df["open"] + data_df["high"] + data_df["low"] + data_df["close"]
        ) / 4
        
        # HA Open: (Prev Open + Prev Close) / 2
        # Для первой свечи используем обычное открытие
        heiken_ashi["open"] = (data_df["open"].shift(1) + data_df["close"].shift(1)) / 2
        heiken_ashi.at[heiken_ashi.index[0], "open"] = data_df["open"].iloc[0]
        
        heiken_ashi["high"] = data_df[["high", "open", "close"]].max(axis=1)
        heiken_ashi["low"] = data_df[["low", "open", "close"]].min(axis=1)

        # Расчет RSI от HA Close
        rsi = ta.rsi(heiken_ashi["close"], length=period_rsi)

        # Расчет StochRSI
        min_rsi = rsi.rolling(period_rsi).min()
        max_rsi = rsi.rolling(period_rsi).max()
        stochrsi_raw = (rsi - min_rsi) / (max_rsi - min_rsi)
        
        # Обработка деления на ноль и бесконечности
        stochrsi_raw = stochrsi_raw.fillna(0).replace([np.inf, -np.inf], 0)

        # Сглаживание (SMA)
        stochrsi_K = ta.sma(stochrsi_raw, length=smoothK)
        stochrsi_D = ta.sma(stochrsi_K, length=smoothD)

        return stochrsi_K * 100, stochrsi_D * 100

    def find_stoch_extrema(self, data_df: pd.DataFrame) -> Tuple[List[Any], List[Any]]:
        """
        Находит индексы локальных экстремумов цены на основе пересечений StochRSI.
        
        Логика (упрощенно):
        - Максимумы (Highs): Группы свечей, где StochK >= StochD. Берется свеча с макс. High в группе.
        - Минимумы (Lows): Группы свечей, где StochK <= StochD. Берется свеча с мин. Low в группе.
        
        Исключает последнюю (текущую/незавершенную) группу.
        
        Возвращает:
            Tuple[List, List]: (Список индексов максимумов, Список индексов минимумов).
        """
        # --- Поиск максимумов (StochK >= StochD) ---
        # Условие: K >= D (и D > 5 для фильтра шума) ИЛИ явная перекупленность (>95)
        stoch_positive_mask = (
            (data_df["stochK"] >= data_df["stochD"]) & (data_df["stochD"] > 5.0)
        ) | ((data_df["stochK"] > 95.0) & (data_df["stochD"] > 95.0))
        
        # Группировка последовательных "положительных" областей
        stoch_group_ids_high = (
            stoch_positive_mask != stoch_positive_mask.shift(1)
        ).cumsum()
        stoch_group_ids_high[~stoch_positive_mask] = np.nan
        
        grouped_df_high = data_df[stoch_positive_mask].copy()
        grouped_df_high["group_id"] = stoch_group_ids_high[stoch_positive_mask]

        # Убираем последнюю группу, если она еще активна (не завершена)
        if (
            not grouped_df_high.empty
            and data_df["stochK"].iloc[-1] >= data_df["stochD"].iloc[-1]
        ):
            last_group_id_high = grouped_df_high["group_id"].iloc[-1]
            grouped_df_high = grouped_df_high[
                grouped_df_high["group_id"] != last_group_id_high
            ]

        # Находим индекс свечи с максимальным High в каждой группе
        max_high_indices = grouped_df_high.loc[
            grouped_df_high.groupby("group_id")["high"].idxmax()
        ].index.tolist()

        # --- Поиск минимумов (StochK <= StochD) ---
        stoch_negative_mask = (
            (data_df["stochK"] <= data_df["stochD"]) & (data_df["stochD"] < 95.0)
        ) | ((data_df["stochK"] < 5.0) & (data_df["stochD"] < 5.0))
        
        stoch_group_ids_low = (
            stoch_negative_mask != stoch_negative_mask.shift(1)
        ).cumsum()
        stoch_group_ids_low[~stoch_negative_mask] = np.nan
        
        grouped_df_low = data_df[stoch_negative_mask].copy()
        grouped_df_low["group_id"] = stoch_group_ids_low[stoch_negative_mask]

        # Убираем последнюю группу
        if (
            not grouped_df_low.empty
            and data_df["stochK"].iloc[-1] <= data_df["stochD"].iloc[-1]
        ):
            last_group_id_low = grouped_df_low["group_id"].iloc[-1]
            grouped_df_low = grouped_df_low[
                grouped_df_low["group_id"] != last_group_id_low
            ]

        # Находим индекс свечи с минимальным Low в каждой группе
        min_low_indices = grouped_df_low.loc[
            grouped_df_low.groupby("group_id")["low"].idxmin()
        ].index.tolist()
        
        return max_high_indices, min_low_indices
