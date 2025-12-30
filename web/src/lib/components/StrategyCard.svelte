<script lang="ts">
  import { activeStrategyId } from "$lib/stores";
  import {
    TrendingUp,
    TrendingDown,
    Activity,
    ChevronRight,
  } from "lucide-svelte";
  import { Badge } from "flowbite-svelte";

  interface Props {
    id: string;
    name: string;
    activeInstruments: number;
    pnl: number;
  }

  let { id, name, activeInstruments, pnl }: Props = $props();

  const isActive = $derived($activeStrategyId === id);
</script>

<button
  class="w-full group p-2 transition-all duration-200 text-left relative overflow-hidden
    {isActive
    ? 'bg-primary-50 dark:bg-primary-900/20 border border-primary-200 dark:border-primary-800 ring-1 ring-primary-500'
    : 'hover:bg-gray-100 dark:hover:bg-gray-800 border border-transparent hover:border-gray-200 dark:hover:border-gray-700'}"
  onclick={() => activeStrategyId.set(id)}
>
  <div class="flex justify-between items-start mb-2">
    <span
      class="font-semibold text-sm truncate pr-2 {isActive
        ? 'text-primary-700 dark:text-primary-400'
        : 'text-gray-700 dark:text-gray-300'}"
    >
      {name}
    </span>
    {#if pnl >= 0}
      <Badge color="green" class="flex gap-1 items-center px-1.5 py-0.5">
        <TrendingUp size={12} />
        {pnl.toFixed(2)}
      </Badge>
    {:else}
      <Badge color="red" class="flex gap-1 items-center px-1.5 py-0.5">
        <TrendingDown size={12} />
        {Math.abs(pnl).toFixed(2)}
      </Badge>
    {/if}
  </div>

  <div class="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
    <div class="flex items-center gap-1.5">
      <div
        class="w-1.5 h-1.5 rounded-full {isActive
          ? 'bg-primary-500 animate-pulse'
          : 'bg-gray-400'}"
      ></div>
      <span>{activeInstruments} coins active</span>
    </div>
  </div>

  {#if isActive}
    <div class="absolute right-2 bottom-2 text-primary-500">
      <ChevronRight size={16} />
    </div>
  {/if}
</button>
