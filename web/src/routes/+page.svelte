<script lang="ts">
  import MainChart from "$lib/components/MainChart.svelte";
  import CoinWatchlist from "$lib/components/CoinWatchlist.svelte";
  import StrategyInspector from "$lib/components/StrategyInspector.svelte";
  import { selectedInstrument, viewMode, showMobileSidebar } from "$lib/stores";
  import { Activity, X } from "lucide-svelte";
  import { onMount } from "svelte";
  import { Drawer } from "flowbite-svelte";
  import { sineIn } from "svelte/easing";

  let isMobile = $state(false);

  onMount(() => {
    const checkMobile = () => {
      isMobile = window.innerWidth < 1024;
      // При инициализации: скрыто на мобильном (true), открыто на десктопе (false)
      showMobileSidebar.set(isMobile);
    };
    checkMobile();
    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
  });
</script>

<svelte:head>
  <title>StrategyScreener | Главная</title>
</svelte:head>

<div
  class="flex h-full w-full overflow-hidden relative bg-white dark:bg-gray-950"
>
  <!-- 1. Левая колонка (Список монет) -->
  <aside
    class="w-[20rem] hidden lg:block border-r border-gray-200 dark:border-gray-800 shrink-0 bg-gray-50/30 dark:bg-gray-900/10 p-1"
  >
    <CoinWatchlist />
  </aside>

  <!-- 2. Центральная область -->
  <div
    class="flex-1 overflow-hidden relative flex flex-col bg-white dark:bg-gray-950 {$viewMode ===
    'watchlist'
      ? 'hidden lg:flex'
      : 'flex'}"
  >
    {#if $selectedInstrument}
      <MainChart />
    {:else}
      <!-- Пустое состояние / Дашборд -->
      <div
        class="flex-1 flex flex-col items-center justify-center p-8 text-center bg-gray-50 dark:bg-gray-950"
      >
        <div
          class="w-16 h-16 bg-primary-100 dark:bg-primary-900/30 rounded-2xl flex items-center justify-center text-primary-600 dark:text-primary-400 mb-6 animate-pulse"
        >
          <Activity size={32} />
        </div>
        <h2 class="text-2xl font-bold text-gray-900 dark:text-white mb-2">
          Добро пожаловать в StrategyScreener
        </h2>
        <p class="text-gray-500 dark:text-gray-400 max-w-md">
          Выберите монету из списка слева, чтобы начать мониторинг и увидеть
          индикаторы активных стратегий в реальном времени.
        </p>
      </div>
    {/if}
  </div>

  <!-- 3. Мобильный оверлей списка монет -->
  {#if $viewMode === "watchlist"}
    <div
      class="lg:hidden absolute inset-0 bg-white dark:bg-gray-950 z-20 overflow-hidden animate-in fade-in slide-in-from-left duration-300"
    >
      <CoinWatchlist />
    </div>
  {/if}

  <!-- 4. Правая панель (Инспектор стратегий) через Drawer -->
  <Drawer
    placement="right"
    bind:open={$showMobileSidebar}
    outsideClickClose={true}
    modal={false}
    class="w-[20rem] bg-gray-50 p-0 dark:bg-gray-900 border-l border-gray-200 dark:border-gray-800 mr-0"
  >
    <StrategyInspector />
  </Drawer>
</div>
