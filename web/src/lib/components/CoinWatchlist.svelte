<script lang="ts">
    import {
        instruments,
        selectCoinStrategy,
        selectedInstrument,
        activeStrategyId,
        activeStrategyDetail,
        strategies,
    } from "$lib/stores";
    import { Search } from "lucide-svelte";
    import {
        Table,
        TableBody,
        TableBodyCell,
        TableBodyRow,
        TableHead,
        TableHeadCell,
        Input,
        Badge,
        Select,
        Label,
    } from "flowbite-svelte";
    import { Filter } from "lucide-svelte";

    let searchQuery = $state("");
    let strategyFilter = $state("all");
    let statusFilter = $state("all");

    const statusOptions = [
        { value: "all", name: "Все статусы" },
        { value: "INTRADE", name: "В СДЕЛКЕ" },
        { value: "PENDING", name: "ОЖИДАНИЕ" },
        { value: "UPDATE", name: "ОБНОВЛЕНИЕ" },
        { value: "WAIT", name: "ЖДЕТ" },
    ];

    const strategyOptions = $derived([
        { value: "all", name: "Все стратегии" },
        ...$strategies.map((s) => ({ value: s.id, name: s.name })),
    ]);

    const filteredInstruments = $derived(
        $instruments
            .map((coin) => {
                // Сначала фильтруем стратегии внутри монеты
                const matchingStrategies = coin.strategies.filter((s) => {
                    const matchStrat =
                        strategyFilter === "all" ||
                        s.strategyId === strategyFilter;
                    const matchStatus =
                        statusFilter === "all" || s.status === statusFilter;
                    return matchStrat && matchStatus;
                });

                return {
                    ...coin,
                    displayStrategies: matchingStrategies,
                };
            })
            .filter((coin) => {
                // Оставляем монету, если она подходит под поиск И у неё остались подходящие стратегии
                const matchSearch = coin.symbol
                    .toLowerCase()
                    .includes(searchQuery.toLowerCase());
                return matchSearch && coin.displayStrategies.length > 0;
            }),
    );

    function isRowActive(symbol: string, strategyId: string) {
        return (
            $selectedInstrument === symbol && $activeStrategyId === strategyId
        );
    }

    function getStatusColor(status: string) {
        switch (status) {
            case "INTRADE":
            case "UPDATE":
                return "green";
            case "PENDING":
                return "yellow";
            default:
                return undefined;
        }
    }

    function getStatusLabel(status: string) {
        switch (status) {
            case "INTRADE":
                return "В СДЕЛКЕ";
            case "UPDATE":
                return "ОБНОВЛЕНИЕ";
            case "PENDING":
                return "ОЖИДАНИЕ";
            case "WAIT":
                return "ЖДЕТ";
            default:
                return status;
        }
    }

    function isHighlight(status: string) {
        return status === "INTRADE" || status === "UPDATE";
    }

    function handleRowClick(symbol: string, strategyId: string) {
        selectCoinStrategy(symbol, strategyId);
        const detail = $strategies.find((s) => s.id === strategyId);
        if (detail) {
            activeStrategyDetail.set(detail);
        }
    }
</script>

<div class="flex flex-col h-full bg-gray-50 dark:bg-gray-900/50">
    <div
        class="px-4 py-2 border-b border-gray-200 dark:border-gray-800 space-y-3"
    >
        <div class="grid grid-cols-2 gap-2">
            <div class="space-y-1">
                <Label
                    class="text-[10px] uppercase font-bold text-gray-400 flex items-center gap-1"
                >
                    <Filter size={10} /> Стратегия
                </Label>
                <Select
                    items={strategyOptions}
                    bind:value={strategyFilter}
                    size="sm"
                    class="text-[11px] py-1 bg-white dark:bg-gray-950 border-gray-200 dark:border-gray-800"
                />
            </div>
            <div class="space-y-1">
                <Label
                    class="text-[10px] uppercase font-bold text-gray-400 flex items-center gap-1"
                >
                    <Filter size={10} /> Статус
                </Label>
                <Select
                    items={statusOptions}
                    bind:value={statusFilter}
                    size="sm"
                    class="text-[11px] py-1 bg-white dark:bg-gray-950 border-gray-200 dark:border-gray-800"
                />
            </div>
        </div>
    </div>

    <div class="flex-1 overflow-y-auto custom-scrollbar">
        <Table hoverable={true} shadow={false} class="border-none w-full">
            <TableHead
                class="bg-gray-100 dark:bg-gray-800/30 sticky top-0 z-10"
            >
                <TableHeadCell class="py-2 px-3 text-[9px]"
                    >Монета</TableHeadCell
                >
                <TableHeadCell class="py-2 px-3 text-[9px] text-center"
                    >Стратегия</TableHeadCell
                >
                <TableHeadCell class="py-2 px-3 text-[9px] text-right"
                    >Статус</TableHeadCell
                >
            </TableHead>
            <TableBody>
                {#each filteredInstruments as coin}
                    {#each coin.displayStrategies as strategy, idx}
                        <TableBodyRow
                            class="cursor-pointer group text-[11px] {isRowActive(
                                coin.symbol,
                                strategy.strategyId,
                            )
                                ? 'bg-primary-50 dark:bg-primary-900/20'
                                : ''} {isHighlight(strategy.status)
                                ? 'bg-green-50/50 dark:bg-green-900/10'
                                : ''}"
                            onclick={() =>
                                handleRowClick(
                                    coin.symbol,
                                    strategy.strategyId,
                                )}
                        >
                            {#if idx === 0}
                                <TableBodyCell
                                    rowspan={coin.displayStrategies.length}
                                    class="font-bold py-2 px-3 border-r border-gray-100 dark:border-gray-800 align-middle bg-white/50 dark:bg-gray-900/50"
                                >
                                    {coin.symbol}
                                </TableBodyCell>
                            {/if}
                            <TableBodyCell
                                class="max-w-[110px] wtext-[8px] break-all py-2 px-3 {isHighlight(
                                    strategy.status,
                                )
                                    ? 'text-green-600 dark:text-green-400 font-semibold'
                                    : 'text-gray-600 dark:text-gray-400'}"
                            >
                                {strategy.strategyName}
                            </TableBodyCell>
                            <TableBodyCell
                                class="py-2 px-3 text-[9px] text-right"
                            >
                                <Badge
                                    color={getStatusColor(strategy.status)}
                                    class="text-[9px] px-1 py-0"
                                >
                                    {getStatusLabel(strategy.status)}
                                </Badge>
                            </TableBodyCell>
                        </TableBodyRow>
                    {/each}
                {/each}
            </TableBody>
        </Table>
    </div>
</div>

<style>
    .custom-scrollbar::-webkit-scrollbar {
        width: 4px;
    }
    .custom-scrollbar::-webkit-scrollbar-thumb {
        background-color: rgba(156, 163, 175, 0.3);
        border-radius: 9999px;
    }
</style>
