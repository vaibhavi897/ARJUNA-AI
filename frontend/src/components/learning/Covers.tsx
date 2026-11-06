/** Notebook cover art and the shelf-book component. */
import { Bookmark, Lock, Plus } from "lucide-react";
import type { NotebookCard } from "../../lib/learning";
import { cn } from "../../lib/utils";

export const COVER: Record<string, { from: string; to: string; ink: string; band: string }> = {
  forest: { from: "#1B5740", to: "#0C3326", ink: "#E6C878", band: "#E6C878" },
  midnight: { from: "#1B2B4B", to: "#0B1226", ink: "#CFE0FF", band: "#7FB0FF" },
  burgundy: { from: "#7A2231", to: "#3F0F18", ink: "#F6D9A8", band: "#E6C878" },
  ocean: { from: "#12707F", to: "#0A3A45", ink: "#D9F5F2", band: "#7EE0D0" },
  amber: { from: "#C48A33", to: "#7A4F14", ink: "#FFF3D6", band: "#3F2A0B" },
  slate: { from: "#475569", to: "#1F2937", ink: "#E2E8F0", band: "#94A3B8" },
  lavender: { from: "#7357C2", to: "#3E2B75", ink: "#EDE5FF", band: "#C4B5FD" },
  terracotta: { from: "#C45F43", to: "#7C321F", ink: "#FFE9DD", band: "#F6D9A8" },
};

export function CoverFace({ style, title, locked, small }: { style: string; title: string; locked?: boolean; small?: boolean }) {
  const c = COVER[style] ?? COVER.forest;
  return (
    <div className="relative h-full w-full overflow-hidden rounded-r-xl rounded-l-[4px]" style={{ background: `linear-gradient(135deg, ${c.from}, ${c.to})` }}>
      <div className="absolute inset-0 opacity-[0.12]" style={{ backgroundImage: "radial-gradient(rgba(255,255,255,.9) 1px, transparent 1px)", backgroundSize: "6px 6px" }} />
      <div className="absolute inset-y-0 left-0 w-[14%] bg-black/25" /><div className="absolute inset-y-3 left-[11%] border-l-2 border-dashed" style={{ borderColor: `${c.ink}66` }} />
      <div className="absolute inset-y-0 right-[13%] w-[7%] opacity-90" style={{ background: c.band }} />
      <div className={cn("absolute inset-0 flex flex-col justify-between pl-[22%] pr-[24%]", small ? "py-3" : "py-6")}>
        <span className="h-px w-8" style={{ background: c.ink }} />
        <h3 className={cn("font-suits font-bold leading-tight tracking-wide", small ? "text-sm" : "text-xl")} style={{ color: c.ink, textShadow: "0 1px 0 rgba(0,0,0,.35)" }}>{title}</h3>
        <span className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-[0.25em]" style={{ color: `${c.ink}AA` }}>{locked ? <><Lock size={11} />Private</> : "Notebook"}</span>
      </div>
    </div>
  );
}

export function ShelfBook({ nb, onOpen, opening }: { nb: NotebookCard; onOpen: () => void; opening?: boolean }) {
  return (
    <button onClick={onOpen} aria-label={`${nb.title}${nb.locked ? ", locked" : ""}, ${nb.pages} pages`} className="group block w-[150px] shrink-0 text-left focus:outline-none sm:w-[170px]">
      <span className="relative block aspect-[3/4]">
        <span className="absolute inset-0 translate-x-1 translate-y-1 rounded-r-xl bg-[#FFFDF6]" aria-hidden />
        <span className="absolute inset-0 translate-x-0.5 translate-y-0.5 rounded-r-xl bg-[#F1EBDA]" aria-hidden />
        <span className={cn("nb-book relative block h-full w-full rounded-r-xl shadow-[10px_14px_24px_-10px_rgba(0,0,0,.55)] group-focus-visible:ring-4 group-focus-visible:ring-brand-400", opening && "nb-opening")}>
          <CoverFace style={nb.cover_style} title={nb.title} locked={nb.locked} />
          {nb.locked ? <span className="absolute -right-2 top-3 grid h-8 w-8 place-items-center rounded-full bg-[#E6C878] text-[#3F2A0B] shadow-lg"><Lock size={15} /></span> : null}
        </span>
      </span>
      <span className="mt-4 block px-1"><span className="block truncate text-sm font-extrabold text-white">{nb.title}</span><span className="text-[11px] text-white/60">{nb.pages} page{nb.pages === 1 ? "" : "s"}{nb.folder ? ` · ${nb.folder}` : ""}</span></span>
    </button>
  );
}

export function NewBook({ onClick }: { onClick: () => void }) {
  return (
    <button onClick={onClick} aria-label="Create a new notebook" className="group w-[150px] shrink-0 text-left focus:outline-none sm:w-[170px]">
      <span className="grid aspect-[3/4] place-items-center rounded-r-xl rounded-l-[4px] border-2 border-dashed border-white/35 text-white/70 transition group-hover:-translate-y-2 group-hover:border-[#E6C878] group-hover:text-[#E6C878] group-focus-visible:ring-4 group-focus-visible:ring-brand-400"><span className="text-center"><Plus size={34} className="mx-auto" /><span className="mt-1 block text-sm font-extrabold">New notebook</span></span></span>
    </button>
  );
}
export { Bookmark };
