<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import {
    createChart,
    ColorType,
    CrosshairMode,
    LineStyle,
    CandlestickSeries,
    HistogramSeries,
    LineSeries,
    createSeriesMarkers,
    type IChartApi,
    type ISeriesApi,
    type CandlestickData,
    type HistogramData,
    type SeriesMarker,
    type Time,
  } from "lightweight-charts";
  import {
    selectedInstrument,
    strategies,
    activeStrategyId,
    activeStrategyDetail,
    fetchCandles,
    fetchTrades,
    fetchInstrumentState,
    getPricePrecision,
    showMobileSidebar,
  } from "$lib/stores";
  import {
    Maximize2,
    RefreshCw,
    Activity,
    Target,
    ShieldAlert,
    Info,
  } from "lucide-svelte";
  import { Button, Badge, ButtonGroup } from "flowbite-svelte";

  let chartContainer: HTMLDivElement;
  let chart: IChartApi;
  let candlestickSeries: ISeriesApi<"Candlestick">;
  let indicatorsSeriesMap = new Map<string, ISeriesApi<"Line" | "Histogram">>();
  let markersPlugin: any;

  // Хранилище ценовых линий для последующего удаления
  let tpLine: any = null;
  let slLine: any = null;
  let entryLine: any = null;

  let currentPosition: any = $state(null);
  let currentOrder: any = $state(null);

  const initData = async () => {
    if (!candlestickSeries || !$selectedInstrument || !$activeStrategyId)
      return;

    // Сброс состояния
    currentPosition = null;
    currentOrder = null;
    clearPriceLines();

    const historical = await fetchCandles(
      $activeStrategyId,
      $selectedInstrument,
    );

    if (historical && historical.length > 0) {
      // Настройка точности цены на основе первой свечи
      const precision = getPricePrecision(historical[0].close);
      candlestickSeries.applyOptions({
        priceFormat: {
          type: "price",
          precision: precision,
          minMove: 1 / Math.pow(10, precision),
        },
      });

      const candleData: CandlestickData[] = historical.map((c: any) => ({
        time: c.timestamp as Time,
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
      }));

      const volumeData: HistogramData[] = historical.map((c: any) => ({
        time: c.timestamp as Time,
        value: c.volume,
        color:
          c.close > c.open
            ? "rgba(16, 185, 129, 0.4)"
            : "rgba(239, 68, 68, 0.4)",
      }));

      candlestickSeries.setData(candleData);

      // --- Отрисовка индикаторов и объемов ---
      // 1. Очистка старых серий
      indicatorsSeriesMap.forEach((s) => chart.removeSeries(s));
      indicatorsSeriesMap.clear();

      if ($activeStrategyDetail?.indicators) {
        Object.entries($activeStrategyDetail.indicators).forEach(
          ([paneName, indicators], paneIndex) => {
            let baseSeries: ISeriesApi<any> =
              paneIndex === 0 ? candlestickSeries : null!;

            Object.entries(indicators as Record<string, any>).forEach(
              ([id, cfg]) => {
                if (cfg.value !== undefined) return;

                const isHistogram = cfg.linestyle === "histogram";
                let series: ISeriesApi<any>;

                if (isHistogram) {
                  series = chart.addSeries(
                    HistogramSeries,
                    {
                      color: cfg.color,
                      title: cfg.label,
                      priceFormat: { type: "volume" },
                      priceScaleId: id,
                    },
                    paneIndex,
                  );
                  chart
                    .priceScale(id)
                    .applyOptions({ scaleMargins: { top: 0.7, bottom: 0 } });
                } else {
                  series = chart.addSeries(
                    LineSeries,
                    {
                      color: cfg.color,
                      title: cfg.label,
                      lineWidth: 2,
                      lineStyle:
                        cfg.linestyle === "dashes"
                          ? LineStyle.Dashed
                          : cfg.linestyle === "dotted"
                            ? LineStyle.Dotted
                            : LineStyle.Solid,
                    },
                    paneIndex,
                  );
                }

                if (!baseSeries) baseSeries = series;
                indicatorsSeriesMap.set(id, series);

                const data = historical
                  .map((c: any) => ({
                    time: c.timestamp as Time,
                    value: c[id] ?? c.indicators?.[id],
                    color:
                      isHistogram && c.close > c.open
                        ? "rgba(16, 185, 129, 0.4)"
                        : isHistogram
                          ? "rgba(239, 68, 68, 0.4)"
                          : undefined,
                  }))
                  .filter((d) => d.value !== undefined && !isNaN(d.value));

                series.setData(data as any);
                /*
                if (cfg.marker) {
                  series.setMarkers(
                    data.map((d) => ({
                      time: d.time,
                      position: "inBar",
                      color: cfg.color,
                      shape: "circle",
                      text: cfg.label,
                    })),
                  );
                }
                */
              },
            );

            // Отрисовка горизонтальных линий
            Object.entries(indicators as Record<string, any>).forEach(
              ([id, cfg]) => {
                if (cfg.value !== undefined && baseSeries) {
                  baseSeries.createPriceLine({
                    price: cfg.value,
                    color: cfg.color,
                    lineWidth: 1,
                    lineStyle:
                      cfg.linestyle === "dotted"
                        ? LineStyle.Dotted
                        : LineStyle.Dashed,
                    axisLabelVisible: true,
                    title: cfg.label,
                  });
                }
              },
            );
          },
        );

        // Настройка высоты панелей
        // @ts-ignore
        const allPanes = chart.panes();
        if (allPanes.length > 1) {
          allPanes[0].setHeight(chartContainer.clientHeight * 0.5);
        }
      }

      // Авто-масштаб после загрузки
      chart.timeScale().fitContent();
    }

    const state = await fetchInstrumentState(
      $activeStrategyId,
      $selectedInstrument,
    );
    currentPosition = state.position || null;
    currentOrder = state.order || null;
    updateActiveLines();

    const trades = await fetchTrades($activeStrategyId, $selectedInstrument);
    const markers: SeriesMarker<Time>[] = trades.flatMap((t: any) => [
      {
        time: t.entry_time as Time,
        position: t.side === "LONG" ? "belowBar" : "aboveBar",
        color: t.side === "LONG" ? "#6366f1" : "#f59e0b",
        shape: t.side === "LONG" ? "arrowUp" : "arrowDown",
        text: "Вход",
      },
      {
        time: t.exit_time as Time,
        position: t.side === "LONG" ? "aboveBar" : "belowBar",
        color: "#94a3b8",
        shape: "circle",
        text: `Выход (${t.pnl > 0 ? "+" : ""}${t.pnl.toFixed(2)})`,
      },
    ]);

    if (markersPlugin) {
      markersPlugin.setMarkers(
        markers.sort((a, b) => (a.time as number) - (b.time as number)),
      );
    }
  };

  function clearPriceLines() {
    if (candlestickSeries) {
      if (tpLine) candlestickSeries.removePriceLine(tpLine);
      if (slLine) candlestickSeries.removePriceLine(slLine);
      if (entryLine) candlestickSeries.removePriceLine(entryLine);
      tpLine = slLine = entryLine = null;
    }
  }

  function updateActiveLines() {
    if (!candlestickSeries || !currentPosition) {
      clearPriceLines();
      return;
    }

    clearPriceLines();

    if (currentPosition.take_profit) {
      tpLine = candlestickSeries.createPriceLine({
        price: currentPosition.take_profit,
        color: "#10b981",
        lineWidth: 2,
        lineStyle: LineStyle.Dashed,
        axisLabelVisible: true,
        title: "TP",
      });
    }

    if (currentPosition.stop_loss) {
      slLine = candlestickSeries.createPriceLine({
        price: currentPosition.stop_loss,
        color: "#ef4444",
        lineWidth: 2,
        lineStyle: LineStyle.Dashed,
        axisLabelVisible: true,
        title: "SL",
      });
    }

    if (currentPosition.entry_price) {
      entryLine = candlestickSeries.createPriceLine({
        price: currentPosition.entry_price,
        color: "#6366f1",
        lineWidth: 1,
        lineStyle: LineStyle.Dotted,
        axisLabelVisible: true,
        title: "ENTRY",
      });
    }
  }

  onMount(() => {
    chart = createChart(chartContainer, {
      layout: {
        background: { type: ColorType.Solid, color: "#030712" },
        textColor: "#9ca3af",
        fontSize: 11,
      },
      grid: {
        vertLines: { color: "rgba(75, 85, 99, 0.2)" },
        horzLines: { color: "rgba(75, 85, 99, 0.2)" },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
      },
      rightPriceScale: {
        borderColor: "rgba(75, 85, 99, 0.2)",
        autoScale: true,
      },
      timeScale: {
        borderColor: "rgba(75, 85, 99, 0.2)",
        timeVisible: true,
        secondsVisible: false,
      },
      autoSize: true,
    });

    candlestickSeries = chart.addSeries(CandlestickSeries, {
      upColor: "#10b981",
      downColor: "#ef4444",
      borderVisible: false,
      wickUpColor: "#10b981",
      wickDownColor: "#ef4444",
    });

    markersPlugin = createSeriesMarkers(candlestickSeries);

    chart.priceScale("right").applyOptions({
      scaleMargins: {
        top: 0.1,
        bottom: 0.2,
      },
    });

    const handleWsMessage = (event: any) => {
      const msg = event.detail;
      if (
        msg.type === "candle_update" &&
        msg.data.symbol === $selectedInstrument
      ) {
        const c = msg.data;
        candlestickSeries.update({
          time: c.timestamp as Time,
          open: c.open,
          high: c.high,
          low: c.low,
          close: c.close,
        });
        // Update indicators and volume
        indicatorsSeriesMap.forEach((series, id) => {
          const val = c[id] ?? c.indicators?.[id];
          if (val !== undefined) {
            const isHistogram = (series as any).seriesType() === "Histogram";
            series.update({
              time: c.timestamp as Time,
              value: val as number,
              color: isHistogram
                ? c.close > c.open
                  ? "rgba(16, 185, 129, 0.4)"
                  : "rgba(239, 68, 68, 0.4)"
                : undefined,
            } as any);
          }
        });
      } else if (
        msg.type === "update" &&
        msg.data.symbol === $selectedInstrument
      ) {
        if (msg.event === "PositionStateEvent") {
          currentPosition = msg.data.side === "FLAT" ? null : msg.data;
          updateActiveLines();
        } else if (msg.event === "TradeTerminalEvent") {
          // Обновляем маркеры при закрытии сделки
          setTimeout(initData, 500); // Небольшая задержка для синхронизации
        }
      }
    };

    window.addEventListener("ws_message", handleWsMessage as EventListener);

    return () => {
      window.removeEventListener(
        "ws_message",
        handleWsMessage as EventListener,
      );
      chart.remove();
    };
  });

  $effect(() => {
    if ($selectedInstrument || $activeStrategyId) {
      initData();
    }
  });
  $effect(() => {
    if (!$activeStrategyDetail && $strategies.length > 0) {
      const current = $strategies.find((s) => s.id === $activeStrategyId);
      if (current) activeStrategyDetail.set(current);
      else activeStrategyDetail.set($strategies[0]);
    }
  });
</script>

<div class="flex flex-col h-full bg-white dark:bg-gray-950">
  <!-- Управление графиком -->
  <div
    class="px-4 py-2 flex justify-between items-center border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900/30"
  >
    <div class="flex items-center gap-3">
      <span class="text-sm font-bold text-gray-900 dark:text-white sm:text-lg"
        >{$selectedInstrument || "Выберите монету"}</span
      >
      {#if $activeStrategyId}
        <Badge
          color="indigo"
          class="text-[10px] py-0.5"
          onclick={() => showMobileSidebar.update((v) => !v)}
          >{$activeStrategyDetail?.name}</Badge
        >
      {/if}
    </div>

    <div class="flex items-center gap-2 scale-90 sm:scale-100">
      <ButtonGroup>
        <Button color="alternative" class="!p-1.5" onclick={initData}
          ><RefreshCw size={16} /></Button
        >
        <Button color="alternative" class="!p-1.5"
          ><Maximize2 size={16} /></Button
        >
      </ButtonGroup>
    </div>
  </div>

  <!-- Холст графика -->
  <div
    class="flex-1 min-h-[300px] bg-gray-950"
    bind:this={chartContainer}
  ></div>

  <!-- Нижняя панель информации -->
  <div
    class="flex flex-col border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 overflow-y-auto max-h-[40%] custom-scrollbar"
  >
    <!-- Ряд 1: Статус активной сделки -->
    <div
      class="px-4 py-3 border-b border-gray-100 dark:border-gray-800 flex items-center gap-6 overflow-x-auto no-scrollbar shrink-0"
    >
      {#if currentPosition}
        <div
          class="flex items-center gap-1.5 p-1 px-2.5 bg-green-500/10 rounded border border-green-500/20 shrink-0"
        >
          <Activity size={14} class="text-green-500" />
          <span class="text-[10px] font-black text-green-500">В СДЕЛКЕ</span>
        </div>

        <div class="flex items-center gap-4 text-sm font-medium shrink-0">
          <div class="flex items-center gap-2">
            <span class="text-gray-400 text-[10px] uppercase font-bold"
              >Вход:</span
            >
            <span class="text-gray-900 dark:text-white font-mono text-xs"
              >{currentPosition.entry_price?.toFixed(2)}</span
            >
          </div>
          <div class="flex items-center gap-2" title="Тейк-профит">
            <Target size={14} class="text-green-500" />
            <span class="text-green-500 font-mono text-xs"
              >{currentPosition.take_profit?.toFixed(2) || "---"}</span
            >
          </div>
          <div class="flex items-center gap-2" title="Стоп-лосс">
            <ShieldAlert size={14} class="text-red-500" />
            <span class="text-red-500 font-mono text-xs"
              >{currentPosition.stop_loss?.toFixed(2) || "---"}</span
            >
          </div>
          <div class="flex items-center gap-2">
            <span
              class="font-mono text-xs {currentPosition.unrealised_pnl >= 0
                ? 'text-green-500'
                : 'text-red-500'}"
            >
              П/У {currentPosition.unrealised_pnl >= 0
                ? "+"
                : ""}{currentPosition.unrealised_pnl?.toFixed(2) || "0.00"}
            </span>
          </div>
        </div>
      {:else if currentOrder}
        <Badge color="yellow"
          >{currentOrder.order_type} @ {currentOrder.price?.toFixed(2)}</Badge
        >
        <span class="text-xs text-gray-500 animate-pulse ml-2"
          >Ожидание исполнения...</span
        >
      {:else}
        <div class="flex items-center gap-2 opacity-50">
          <Activity size={14} class="text-gray-400" />
          <span
            class="text-[10px] font-bold text-gray-500 uppercase tracking-widest"
            >Поиск сигналов для входа...</span
          >
        </div>
      {/if}
    </div>
  </div>
</div>

<style>
  .no-scrollbar::-webkit-scrollbar {
    display: none;
  }
  .no-scrollbar {
    -ms-overflow-style: none;
    scrollbar-width: none;
  }
  .custom-scrollbar::-webkit-scrollbar {
    width: 4px;
  }
  .custom-scrollbar::-webkit-scrollbar-thumb {
    background-color: rgba(156, 163, 175, 0.3);
    border-radius: 9999px;
  }
</style>
