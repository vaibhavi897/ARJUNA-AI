/** Recharts wrappers with one consistent visual language. */
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { CHART_COLORS, formatDate, scoreTone } from "../lib/utils";

const AXIS = { fontSize: 11, fill: "#7D8F86" };
const GRID = "#EAF4EC";

function TooltipBox({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-xl border border-line bg-white px-3 py-2 shadow-float">
      {label ? <p className="mb-1 text-xs font-bold text-ink-800">{label}</p> : null}
      {payload.map((entry: any) => (
        <p key={entry.dataKey ?? entry.name} className="text-xs text-ink-600">
          <span
            className="mr-1.5 inline-block h-2 w-2 rounded-full align-middle"
            style={{ backgroundColor: entry.color ?? entry.fill }}
          />
          {entry.name}:{" "}
          <span className="font-bold tabular-nums text-ink-900">
            {typeof entry.value === "number" ? Math.round(entry.value * 10) / 10 : entry.value}
          </span>
        </p>
      ))}
    </div>
  );
}

/** Horizontal role-score comparison. */
export function RoleScoreBars({
  data,
  height = 320,
  onSelect,
}: {
  data: { role_name: string; short_label: string | null; score: number; role_slug: string }[];
  height?: number;
  onSelect?: (slug: string) => void;
}) {
  const rows = data.map((item) => ({
    name: item.short_label || item.role_name,
    score: item.score,
    slug: item.role_slug,
  }));

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={rows} layout="vertical" margin={{ left: 8, right: 28, top: 4, bottom: 4 }}>
        <CartesianGrid horizontal={false} stroke={GRID} />
        <XAxis type="number" domain={[0, 100]} tick={AXIS} axisLine={false} tickLine={false} />
        <YAxis
          type="category"
          dataKey="name"
          width={118}
          tick={{ ...AXIS, fontSize: 11.5 }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip content={<TooltipBox />} cursor={{ fill: "rgba(234,244,236,0.6)" }} />
        <Bar
          dataKey="score"
          name="Readiness"
          radius={[0, 6, 6, 0]}
          barSize={16}
          onClick={(entry: any) => onSelect?.(entry?.slug)}
          cursor={onSelect ? "pointer" : undefined}
        >
          {rows.map((row) => (
            <Cell key={row.slug} fill={scoreTone(row.score)} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

/** Skill coverage by category. */
export function SkillRadar({
  data,
  height = 280,
}: {
  data: { label: string; value: number }[];
  height?: number;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <RadarChart data={data} outerRadius="72%">
        <PolarGrid stroke={GRID} />
        <PolarAngleAxis dataKey="label" tick={{ ...AXIS, fontSize: 10.5 }} />
        <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
        <Radar
          name="Average proficiency"
          dataKey="value"
          stroke="#187C4F"
          fill="#44B47C"
          fillOpacity={0.35}
          strokeWidth={2}
        />
        <Tooltip content={<TooltipBox />} />
      </RadarChart>
    </ResponsiveContainer>
  );
}

/** Expected vs actual proficiency for a role's rubric skills. */
export function SkillComparisonBars({
  data,
  height = 360,
}: {
  data: { skill_name: string; expected_value: number; student_value: number }[];
  height?: number;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} layout="vertical" margin={{ left: 8, right: 20, top: 4, bottom: 4 }}>
        <CartesianGrid horizontal={false} stroke={GRID} />
        <XAxis type="number" domain={[0, 100]} tick={AXIS} axisLine={false} tickLine={false} />
        <YAxis
          type="category"
          dataKey="skill_name"
          width={150}
          tick={{ ...AXIS, fontSize: 11 }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip content={<TooltipBox />} cursor={{ fill: "rgba(234,244,236,0.6)" }} />
        <Legend wrapperStyle={{ fontSize: 11, paddingTop: 8 }} />
        <Bar dataKey="expected_value" name="Role expects" fill="#C7DCCD" radius={[0, 4, 4, 0]} barSize={9} />
        <Bar dataKey="student_value" name="You have" fill="#187C4F" radius={[0, 4, 4, 0]} barSize={9} />
      </BarChart>
    </ResponsiveContainer>
  );
}

/** Score history over time, one line per role. */
export function ScoreHistoryChart({
  series,
  height = 300,
}: {
  series: { role_name: string; points: { at: string; score: number }[] }[];
  height?: number;
}) {
  const timestamps = Array.from(
    new Set(series.flatMap((entry) => entry.points.map((point) => point.at)))
  ).sort();

  const rows = timestamps.map((at) => {
    const row: Record<string, any> = { at, label: formatDate(at) };
    for (const entry of series) {
      const point = entry.points.find((item) => item.at === at);
      if (point) row[entry.role_name] = point.score;
    }
    return row;
  });

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={rows} margin={{ left: -10, right: 12, top: 8, bottom: 4 }}>
        <CartesianGrid stroke={GRID} />
        <XAxis dataKey="label" tick={AXIS} axisLine={false} tickLine={false} />
        <YAxis domain={[0, 100]} tick={AXIS} axisLine={false} tickLine={false} />
        <Tooltip content={<TooltipBox />} />
        <Legend wrapperStyle={{ fontSize: 11, paddingTop: 8 }} />
        {series.map((entry, index) => (
          <Line
            key={entry.role_name}
            type="monotone"
            dataKey={entry.role_name}
            stroke={CHART_COLORS[index % CHART_COLORS.length]}
            strokeWidth={2.25}
            dot={{ r: 3, strokeWidth: 0 }}
            activeDot={{ r: 5 }}
            connectNulls
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}

/** Overall readiness trend. */
export function OverallTrend({
  data,
  height = 180,
}: {
  data: { at: string; score: number }[];
  height?: number;
}) {
  const rows = data.map((point) => ({ ...point, label: formatDate(point.at) }));
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={rows} margin={{ left: -18, right: 8, top: 8, bottom: 0 }}>
        <defs>
          <linearGradient id="trendFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#44B47C" stopOpacity={0.45} />
            <stop offset="100%" stopColor="#44B47C" stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke={GRID} vertical={false} />
        <XAxis dataKey="label" tick={AXIS} axisLine={false} tickLine={false} />
        <YAxis domain={[0, 100]} tick={AXIS} axisLine={false} tickLine={false} />
        <Tooltip content={<TooltipBox />} />
        <Area
          type="monotone"
          dataKey="score"
          name="Average readiness"
          stroke="#187C4F"
          strokeWidth={2.25}
          fill="url(#trendFill)"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

/** Simple categorical distribution bars (skills by category, etc.). */
export function CategoryBars({
  data,
  height = 240,
  color = "#229A63",
}: {
  data: { label: string; count: number }[];
  height?: number;
  color?: string;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ left: -18, right: 8, top: 8, bottom: 4 }}>
        <CartesianGrid stroke={GRID} vertical={false} />
        <XAxis
          dataKey="label"
          tick={{ ...AXIS, fontSize: 10 }}
          axisLine={false}
          tickLine={false}
          interval={0}
          angle={-18}
          textAnchor="end"
          height={52}
        />
        <YAxis allowDecimals={false} tick={AXIS} axisLine={false} tickLine={false} />
        <Tooltip content={<TooltipBox />} cursor={{ fill: "rgba(234,244,236,0.6)" }} />
        <Bar dataKey="count" name="Skills" fill={color} radius={[6, 6, 0, 0]} barSize={28} />
      </BarChart>
    </ResponsiveContainer>
  );
}

/** Domain averages as a stacked comparison. */
export function DomainAverageBars({
  data,
  height = 260,
}: {
  data: { domain_name: string; average_score: number; best_score: number }[];
  height?: number;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ left: -18, right: 8, top: 8, bottom: 4 }}>
        <CartesianGrid stroke={GRID} vertical={false} />
        <XAxis
          dataKey="domain_name"
          tick={{ ...AXIS, fontSize: 10 }}
          axisLine={false}
          tickLine={false}
          interval={0}
          angle={-18}
          textAnchor="end"
          height={62}
        />
        <YAxis domain={[0, 100]} tick={AXIS} axisLine={false} tickLine={false} />
        <Tooltip content={<TooltipBox />} cursor={{ fill: "rgba(234,244,236,0.6)" }} />
        <Legend wrapperStyle={{ fontSize: 11, paddingTop: 6 }} />
        <Bar dataKey="average_score" name="Domain average" fill="#A8E1C0" radius={[6, 6, 0, 0]} barSize={18} />
        <Bar dataKey="best_score" name="Best role" fill="#187C4F" radius={[6, 6, 0, 0]} barSize={18} />
      </BarChart>
    </ResponsiveContainer>
  );
}
