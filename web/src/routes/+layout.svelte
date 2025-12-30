<script lang="ts">
  import { onMount } from "svelte";
  import {
    fetchStrategies,
    fetchInstruments,
    initWebSocket,
    activeStrategyId,
    viewMode,
    showWatchlist,
    showMobileSidebar,
    desktopInspectorOpen,
  } from "$lib/stores";
  import { Button } from "flowbite-svelte";
  import {
    Activity,
    LayoutGrid,
    BarChart2,
    PanelRightOpen,
  } from "lucide-svelte";
  import "../app.css";

  let { children } = $props();

  onMount(() => {
    document.documentElement.classList.add("dark");
    fetchStrategies();
    fetchInstruments();
    activeStrategyId.subscribe((id) => {
      if (id) initWebSocket(id);
    });
  });

  function toggleMobileInspector() {
    showMobileSidebar.update((v) => !v);
  }
</script>

<div
  class="flex flex-col h-screen w-screen overflow-hidden bg-white dark:bg-gray-950 font-sans antialiased text-gray-900 dark:text-gray-100"
>
  <!-- Шапка -->
  <header
    class="h-14 flex items-center justify-between px-4 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900/50 backdrop-blur-md z-30 shrink-0"
  >
    <div class="flex items-center gap-3">
      <!-- Мобильная навигация -->
      <div class="lg:hidden">
        {#if $viewMode === "chart"}
          <button
            class="p-2 text-primary-600 transition-colors"
            onclick={showWatchlist}
          >
            <LayoutGrid size={24} />
          </button>
        {:else}
          <div class="px-2 text-gray-400">
            <Activity size={22} />
          </div>
        {/if}
      </div>

      <div class="flex items-center gap-2">
        <div
          class="w-9 h-9 bg-gradient-to-br from-primary-600 to-indigo-700 rounded-xl flex items-center justify-center shadow-lg shadow-primary-500/20 text-white"
        >
          <Activity size={22} />
        </div>
        <div class="flex flex-col leading-none">
          <span class="text-sm font-black tracking-tight uppercase"
            >StrategyScreener</span
          >
          <span
            class="text-[9px] text-gray-400 font-bold uppercase tracking-widest mt-0.5"
            >Terminal v2.0</span
          >
        </div>
      </div>
    </div>

    <!-- Правая часть хедера (Триггер инспектора) -->
    <div class="flex items-center">
      <button
        class="p-2 text-primary-600 transition-colors hover:bg-primary-50 dark:hover:bg-primary-900/20 rounded-lg"
        onclick={() => showMobileSidebar.update((v) => !v)}
        title="Открыть/Закрыть панель стратегий"
      >
        <BarChart2 size={22} />
      </button>
    </div>
  </header>

  <main class="flex-1 overflow-hidden relative">
    {@render children()}
  </main>
</div>

<style>
  :global(:root) {
    --primary-main: #6366f1;
  }
</style>
