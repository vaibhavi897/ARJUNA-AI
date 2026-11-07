/** Language picker. Language names are shown in their own script and are never translated. */
import { Globe, Loader2 } from "lucide-react";
import { useI18n } from "../lib/i18n";
import { cn } from "../lib/utils";

export default function LanguageSwitcher({ dark, className }: { dark?: boolean; className?: string }) {
  const { lang, setLang, languages, busy } = useI18n();
  return (
    <label className={cn("notranslate inline-flex items-center gap-1.5 rounded-xl border px-2.5 py-1.5 text-sm font-semibold", dark ? "border-white/25 bg-white/5 text-white" : "border-line bg-white text-ink-700", className)} translate="no">
      {busy ? <Loader2 size={15} className="animate-spin" /> : <Globe size={15} />}
      <span className="sr-only">Language</span>
      <select value={lang} onChange={(e) => setLang(e.target.value)} aria-label="Language" className={cn("max-w-[9.5rem] cursor-pointer bg-transparent outline-none", dark && "[&>option]:text-black")}>
        {languages.map((l) => <option key={l.code} value={l.code}>{l.name}</option>)}
      </select>
    </label>
  );
}
