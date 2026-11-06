/** ECharts pay-range chart: floating range bars per level with the median line on top. */
import ReactECharts from "echarts-for-react";

export type LevelPay = { name: string; low: number; high: number; base: number; total?: number };

export default function SalaryRange({ data, fmt }: { data: LevelPay[]; fmt: (v: number) => string }) {
  const option = {
    animationDuration: 900, animationEasing: "cubicOut", grid: { left: 8, right: 16, top: 28, bottom: 8, containLabel: true },
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" }, formatter: (p: any[]) => { const d = data[p[0].dataIndex]; return `<b>${d.name}</b><br/>Range: ${fmt(d.low)} to ${fmt(d.high)}<br/>Base: ${fmt(d.base)}${d.total ? `<br/>Total comp: ${fmt(d.total)}` : ""}`; } },
    legend: { top: 0, right: 0, textStyle: { color: "#64748B", fontSize: 11 }, data: ["Range", "Base", "Total compensation"] },
    xAxis: { type: "category", data: data.map((d) => d.name), axisTick: { show: false }, axisLine: { lineStyle: { color: "#CBD5CF" } }, axisLabel: { color: "#334155", fontWeight: 700 } },
    yAxis: { type: "value", axisLabel: { color: "#64748B", formatter: (v: number) => fmt(v) }, splitLine: { lineStyle: { color: "#E8EEEA" } } },
    series: [
      { name: "low", type: "bar", stack: "r", silent: true, itemStyle: { color: "transparent" }, data: data.map((d) => d.low), tooltip: { show: false } },
      { name: "Range", type: "bar", stack: "r", barWidth: 38, itemStyle: { borderRadius: 10, color: { type: "linear", x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: "#6EE7B7" }, { offset: 1, color: "#187C4F" }] } }, data: data.map((d) => d.high - d.low) },
      { name: "Base", type: "line", smooth: true, symbolSize: 10, lineStyle: { width: 3, color: "#0C3326" }, itemStyle: { color: "#0C3326" }, data: data.map((d) => d.base) },
      ...(data.some((d) => d.total) ? [{ name: "Total compensation", type: "line", smooth: true, symbolSize: 9, lineStyle: { width: 3, type: "dashed", color: "#E6C878" }, itemStyle: { color: "#C9A24B" }, data: data.map((d) => d.total ?? null) }] : []),
    ],
  };
  return <ReactECharts option={option} style={{ height: 300 }} notMerge lazyUpdate />;
}
