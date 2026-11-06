/** FullCalendar-powered plan calendar: drag tasks between days, colour-coded by category. */
import { useEffect, useMemo, useRef } from "react";
import FullCalendar from "@fullcalendar/react";
import dayGridPlugin from "@fullcalendar/daygrid";
import interactionPlugin from "@fullcalendar/interaction";
import type { EventDropArg } from "@fullcalendar/core";
import type { Day } from "../../lib/learning";
import { iso, parse } from "./shared";

const COLORS: Record<string, { bg: string; fg: string; border: string }> = {
  learn: { bg: "#ECFDF5", fg: "#047857", border: "#A7F3D0" },
  practice: { bg: "#F0F9FF", fg: "#0369A1", border: "#BAE6FD" },
  project: { bg: "#F5F3FF", fg: "#6D28D9", border: "#DDD6FE" },
  revision: { bg: "#FFFBEB", fg: "#B45309", border: "#FDE68A" },
  assessment: { bg: "#FFF1F2", fg: "#BE123C", border: "#FECDD3" },
  milestone: { bg: "#FDF4FF", fg: "#A21CAF", border: "#F5D0FE" },
};

export default function PlanCalendar({ view, cursor, days, planStart, planEnd, selected, onSelect, onMove }: {
  view: "month" | "week"; cursor: Date; days: Map<string, Day>; planStart: string; planEnd: string; selected: string | null;
  onSelect: (d: string) => void; onMove: (taskId: number, to: string) => void;
}) {
  const ref = useRef<FullCalendar>(null);
  useEffect(() => { const api = ref.current?.getApi(); if (api) { api.changeView(view === "month" ? "dayGridMonth" : "dayGridWeek"); api.gotoDate(cursor); } }, [view, cursor]);

  const events = useMemo(() => {
    const out: any[] = [];
    days.forEach((d) => {
      d.tasks.filter((t) => t.category !== "rest").forEach((t) => {
        const c = COLORS[t.category] ?? COLORS.learn;
        out.push({
          id: `t${t.id}`, title: t.title, start: d.date, allDay: true,
          backgroundColor: c.bg, textColor: c.fg, borderColor: t.missed ? "#F43F5E" : c.border,
          editable: t.status === "pending" && !t.locked,
          classNames: [t.status === "completed" ? "fc-done" : "", t.status === "skipped" ? "fc-skipped" : ""],
          extendedProps: { taskId: t.id },
        });
      });
      if (d.milestone) out.push({ id: `m${d.milestone.id}`, title: `Milestone: ${d.milestone.title}`, start: d.date, allDay: true, backgroundColor: COLORS.milestone.bg, textColor: COLORS.milestone.fg, borderColor: COLORS.milestone.border, editable: false });
    });
    return out;
  }, [days]);

  const ps = parse(planStart), pe = parse(planEnd);
  const drop = (a: EventDropArg) => {
    const id = a.event.extendedProps.taskId as number | undefined;
    if (!id || !a.event.start) { a.revert(); return; }
    const to = iso(a.event.start);
    const dd = days.get(to);
    if (a.event.start < ps || a.event.start > pe || dd?.rest) { a.revert(); return; }
    onMove(id, to);
  };

  return (
    <div className="plan-cal rounded-2xl border border-line bg-white p-2">
      <FullCalendar
        ref={ref}
        plugins={[dayGridPlugin, interactionPlugin]}
        initialView={view === "month" ? "dayGridMonth" : "dayGridWeek"}
        initialDate={cursor}
        headerToolbar={false}
        firstDay={1}
        height="auto"
        fixedWeekCount={false}
        editable
        eventStartEditable
        eventDurationEditable={false}
        events={events}
        eventOrder="start"
        dayMaxEvents={view === "month" ? 3 : false}
        eventDrop={drop}
        dateClick={(i) => onSelect(i.dateStr)}
        eventClick={(i) => { if (i.event.start) onSelect(iso(i.event.start)); }}
        dayCellClassNames={(a) => {
          const k = iso(a.date), d = days.get(k);
          return [a.date < ps || a.date > pe ? "fc-outside-plan" : "", d?.rest ? "fc-restday" : "", selected === k ? "fc-selected" : ""];
        }}
      />
    </div>
  );
}
