<script lang="ts">
  import {
    strategies,
    activeStrategyId,
    activeStrategyDetail,
  } from "$lib/stores";
  import { ShieldCheck, Info, ChevronRight, BarChart2 } from "lucide-svelte";

  function handleStrategyClick(strategy: any) {
    activeStrategyId.set(strategy.id);
    activeStrategyDetail.set(strategy);
  }

  // Установка детали по умолчанию (Svelte 5 effect)
  $effect(() => {
    if (!$activeStrategyDetail && $strategies.length > 0) {
      const current = $strategies.find((s) => s.id === $activeStrategyId);
      if (current) activeStrategyDetail.set(current);
      else activeStrategyDetail.set($strategies[0]);
    }
  });
</script>

<div
  class="h-full flex flex-col bg-gray-50 dark:bg-gray-900 border-l border-gray-200 dark:border-gray-800"
>
  <!-- Верх: Список стратегий -->
  <div
    class="flex-1 flex flex-col min-h-[40%] border-b border-gray-200 dark:border-gray-800"
  >
    <div
      class="px-4 py-3 bg-white dark:bg-gray-800/50 border-b border-gray-200 dark:border-gray-800"
    >
      <h2
        class="text-xs font-bold text-gray-500 uppercase tracking-widest flex items-center gap-2"
      >
        <ShieldCheck size={12} class="text-primary-500" />
        Доступные стратегии
      </h2>
    </div>

    <div class="flex-1 overflow-y-auto p-2 space-y-1 custom-scrollbar">
      {#each $strategies as strategy}
        <button
          class="w-full text-left px-3 py-2.5 rounded-lg text-sm transition-all duration-200 group flex items-center justify-between
            {$activeStrategyId === strategy.id
            ? 'bg-primary-500 text-white shadow-lg shadow-primary-500/20'
            : 'text-gray-600 dark:text-gray-400 hover:bg-white dark:hover:bg-gray-800'}"
          onclick={() => handleStrategyClick(strategy)}
        >
          <div class="flex items-center gap-2">
            <BarChart2
              size={16}
              class={$activeStrategyId === strategy.id
                ? "text-white"
                : "text-gray-400"}
            />
            <span class="font-medium">{strategy.name}</span>
          </div>
          <ChevronRight
            size={14}
            class={$activeStrategyId === strategy.id
              ? "text-white"
              : "text-gray-600 dark:text-gray-700"}
          />
        </button>
      {/each}
    </div>
  </div>

  <!-- Низ: Описание стратегии -->
  <div
    class="flex-1 overflow-y-auto p-4 bg-gray-100/50 dark:bg-gray-950/20 custom-scrollbar"
  >
    {#if $activeStrategyDetail}
      <div class="space-y-4">
        <div class="flex items-center gap-2 text-primary-500">
          <Info size={16} />
          <h3
            class="font-bold text-sm tracking-tight text-gray-900 dark:text-white"
          >
            Инфобаза стратегии
          </h3>
        </div>

        <div
          class="bg-white dark:bg-gray-800 p-4 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm"
        >
          <h4 class="text-lg font-black text-gray-900 dark:text-white mb-2">
            {$activeStrategyDetail.name}
          </h4>
          <p class="text-xs leading-relaxed text-gray-600 dark:text-gray-400">
            {$activeStrategyDetail.description ||
              "Описание для данной конфигурации стратегии отсутствует."}
          </p>

          <div
            class="mt-4 pt-4 border-t border-gray-100 dark:border-gray-700 flex flex-col gap-2"
          >
            <div class="flex justify-between items-center text-[10px]">
              <span class="text-gray-500 uppercase tracking-wider font-semibold"
                >Активные пары</span
              >
              <span class="text-gray-900 dark:text-white font-bold"
                >{$activeStrategyDetail.activeInstruments}</span
              >
            </div>
            <div class="flex justify-between items-center text-[10px]">
              <span class="text-gray-500 uppercase tracking-wider font-semibold"
                >Общий PnL</span
              >
              <span
                class={$activeStrategyDetail.pnl >= 0
                  ? "text-green-500 font-bold"
                  : "text-red-500 font-bold"}
              >
                {$activeStrategyDetail.pnl >= 0
                  ? "+"
                  : ""}{$activeStrategyDetail.pnl.toFixed(2)}
              </span>
            </div>
          </div>
        </div>
      </div>
    {:else}
      <div
        class="h-full flex flex-col items-center justify-center text-center p-6 opacity-30"
      >
        <Info size={32} class="mb-2" />
        <p class="text-xs">
          Выберите стратегию из списка для просмотра тех. характеристик
        </p>
      </div>
    {/if}
  </div>
</div>
