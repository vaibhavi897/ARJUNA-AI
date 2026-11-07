/**
 * Site-wide translation. The app is written in English; when another language is chosen, every visible piece of text
 * (including AI-written content) is translated through the backend (Sarvam AI) and swapped in place.
 *
 *  - strings are cached in the browser and in the database, so each distinct text is translated once;
 *  - user input, code editors and code blocks are never touched;
 *  - switching back to English restores the original text exactly;
 *  - if translation is unavailable the site stays in English and says why.
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { request } from "./api";
import { useToast } from "./auth";

export type Language = { code: string; name: string };
export const DEFAULT_LANG = "en-IN";
const LS_LANG = "arjuna.lang";
const LS_CACHE = (l: string) => `arjuna.tr.${l}`;
const MAX_CACHE = 4000;
const ATTRS = ["placeholder", "title", "aria-label", "alt"] as const;
const SKIP_TAGS = new Set(["SCRIPT", "STYLE", "TEXTAREA", "INPUT", "SELECT", "OPTION", "CODE", "PRE", "NOSCRIPT", "KBD", "IFRAME", "CANVAS"]);
const SKIP_SELECTOR = "[translate=no], .notranslate, [contenteditable=true], .ProseMirror, .monaco-editor, .fc-toolbar-title";
const BRAND = /^(arjuna(\s+ai)?|ai|careerverse|gemini|sarvam|pdf|docx|word|linkedin|github)$/i;
const HAS_LETTERS = /[A-Za-z]{2,}/;

type Ctx = { lang: string; setLang: (code: string) => void; languages: Language[]; busy: boolean; configured: boolean | null };
const I18nContext = createContext<Ctx | null>(null);

export function useI18n(): Ctx {
  const c = useContext(I18nContext);
  if (!c) throw new Error("useI18n must be used inside LanguageProvider");
  return c;
}

const FALLBACK_LANGS: Language[] = [
  { code: "en-IN", name: "English" }, { code: "hi-IN", name: "हिन्दी (Hindi)" }, { code: "mr-IN", name: "मराठी (Marathi)" }, { code: "gu-IN", name: "ગુજરાતી (Gujarati)" },
  { code: "bn-IN", name: "বাংলা (Bengali)" }, { code: "ta-IN", name: "தமிழ் (Tamil)" }, { code: "te-IN", name: "తెలుగు (Telugu)" }, { code: "kn-IN", name: "ಕನ್ನಡ (Kannada)" },
  { code: "ml-IN", name: "മലയാളം (Malayalam)" }, { code: "pa-IN", name: "ਪੰਜਾਬੀ (Punjabi)" }, { code: "od-IN", name: "ଓଡ଼ିଆ (Odia)" },
];

function readCache(lang: string): Map<string, string> {
  try { return new Map(Object.entries(JSON.parse(localStorage.getItem(LS_CACHE(lang)) || "{}"))); } catch { return new Map(); }
}
function writeCache(lang: string, m: Map<string, string>) {
  try {
    const entries = [...m.entries()].slice(-MAX_CACHE);
    localStorage.setItem(LS_CACHE(lang), JSON.stringify(Object.fromEntries(entries)));
  } catch { /* storage full or blocked: the server cache still helps */ }
}

class Engine {
  private cache: Map<string, string>;
  private textInfo = new WeakMap<Text, { orig: string; shown: string }>();
  private attrInfo = new WeakMap<Element, Record<string, { orig: string; shown: string }>>();
  private groups = new WeakMap<Element, { nodes: Text[]; origs: string[]; shown: string }>();
  private seen = new Set<Element>();
  private pending = new Set<string>();
  private inflight = false;
  private timer: number | null = null;
  private obs: MutationObserver | null = null;
  private dirty = new Set<Node>();
  private stopped = false;

  constructor(private lang: string, private onError: (msg: string) => void, private onBusy: (b: boolean) => void) {
    this.cache = readCache(lang);
  }

  start() {
    this.scan(document.body);
    this.obs = new MutationObserver((muts) => {
      for (const m of muts) {
        if (m.type === "characterData") this.dirty.add(m.target);
        else if (m.type === "attributes") this.dirty.add(m.target);
        else m.addedNodes.forEach((n) => this.dirty.add(n));
      }
      this.schedule();
    });
    this.obs.observe(document.body, { childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: [...ATTRS] });
  }

  stop(restore: boolean) {
    this.stopped = true;
    this.obs?.disconnect();
    if (this.timer) clearTimeout(this.timer);
    if (restore) this.restore(document.body);
  }

  private schedule() {
    if (this.timer) return;
    this.timer = window.setTimeout(() => {
      this.timer = null;
      const nodes = [...this.dirty]; this.dirty.clear();
      for (const n of nodes) if (n.isConnected) this.scan(n);
    }, 120);
  }

  private skipped(el: Element | null): boolean {
    for (let e = el; e; e = e.parentElement) {
      if (SKIP_TAGS.has(e.tagName)) return true;
      if (e.matches?.(SKIP_SELECTOR)) return true;
    }
    return false;
  }

  private wanted(s: string): boolean {
    const t = s.trim();
    return t.length > 1 && t.length <= 4000 && HAS_LETTERS.test(t) && !BRAND.test(t) && !/^https?:\/\//i.test(t) && !/^[\w.+-]+@[\w-]+\.[\w.]+$/.test(t);
  }

  private scan(root: Node) {
    if (this.stopped) return;
    if (root.nodeType === Node.TEXT_NODE) { this.handleText(root as Text); this.flush(); return; }
    if (root.nodeType !== Node.ELEMENT_NODE) return;
    const el = root as Element;
    if (this.skipped(el)) return;
    this.seen.clear();
    const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    let n: Node | null;
    while ((n = walker.nextNode())) this.handleText(n as Text);
    this.handleAttrs(el);
    el.querySelectorAll("[placeholder],[title],[aria-label],[alt]").forEach((e) => this.handleAttrs(e));
    this.flush();
  }

  /** An element whose children are ONLY text nodes (two or more): React's way of rendering `Hi {name}, welcome`. */
  private groupParent(node: Text): Element | null {
    const p = node.parentElement;
    if (!p || p.childNodes.length < 2) return null;
    for (const c of Array.from(p.childNodes)) if (c.nodeType !== Node.TEXT_NODE) return null;
    return p;
  }

  private handleGroup(p: Element) {
    const nodes = Array.from(p.childNodes) as Text[];
    const current = nodes.map((n) => n.nodeValue ?? "");
    const g = this.groups.get(p);
    const same = !!g && g.nodes.length === nodes.length && g.nodes.every((n, i) => n === nodes[i]);
    if (same && current[0] === g!.shown && current.slice(1).every((v) => v === "")) return;       // our own translation, untouched
    let origs = current.slice();
    if (same) {                                                                                   // React changed some nodes: rebuild the English
      origs = current.map((v, i) => (i > 0 && v === "" ? g!.origs[i] : v));
      if (current[0] === g!.shown) origs[0] = g!.origs[0];
    }
    const full = origs.join("");
    const setAll = (vals: string[]) => nodes.forEach((n, i) => { if (n.nodeValue !== vals[i]) n.nodeValue = vals[i]; });
    if (!this.wanted(full) || this.skipped(p)) { setAll(origs); this.groups.delete(p); return; }
    const key = full.trim();
    const hit = this.cache.get(key);
    if (hit === undefined) { setAll(origs); this.groups.delete(p); this.pending.add(key); return; }
    const lead = full.match(/^\s*/)![0], trail = full.match(/\s*$/)![0];
    const shown = lead + hit + trail;
    this.groups.set(p, { nodes, origs, shown });
    setAll([shown, ...nodes.slice(1).map(() => "")]);
  }

  private handleText(node: Text) {
    const gp = this.groupParent(node);
    if (gp) { if (!this.seen.has(gp)) { this.seen.add(gp); this.handleGroup(gp); } return; }
    const v = node.nodeValue ?? "";
    const info = this.textInfo.get(node);
    if (info && info.shown === v) return;                       // our own translation
    if (!this.wanted(v) || this.skipped(node.parentElement)) return;
    const key = v.trim();
    const hit = this.cache.get(key);
    if (hit !== undefined) { this.applyText(node, v, key, hit); return; }
    this.pending.add(key);
  }

  private applyText(node: Text, raw: string, key: string, tr: string) {
    const lead = raw.match(/^\s*/)![0], trail = raw.match(/\s*$/)![0];
    const shown = lead + tr + trail;
    this.textInfo.set(node, { orig: raw, shown });
    node.nodeValue = shown;
  }

  private handleAttrs(el: Element) {
    if (this.skipped(el)) return;
    for (const a of ATTRS) {
      const v = el.getAttribute(a);
      if (!v) continue;
      const rec = (this.attrInfo.get(el) ?? {}) as Record<string, { orig: string; shown: string }>;
      if (rec[a] && rec[a].shown === v) continue;
      if (!this.wanted(v)) continue;
      const hit = this.cache.get(v.trim());
      if (hit !== undefined) { rec[a] = { orig: v, shown: hit }; this.attrInfo.set(el, rec); el.setAttribute(a, hit); }
      else this.pending.add(v.trim());
    }
  }

  private restore(root: Node) {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    let n: Node | null;
    while ((n = walker.nextNode())) {
      const t = n as Text;
      const g = t.parentElement ? this.groups.get(t.parentElement) : undefined;
      if (g && g.nodes[0] === t && t.nodeValue === g.shown) { g.nodes.forEach((x, i) => { x.nodeValue = g.origs[i]; }); continue; }
      const info = this.textInfo.get(t);
      if (info && t.nodeValue === info.shown) t.nodeValue = info.orig;
    }
    (root as Element).querySelectorAll?.("[placeholder],[title],[aria-label],[alt]").forEach((e) => {
      const rec = this.attrInfo.get(e);
      if (!rec) return;
      for (const [a, i] of Object.entries(rec)) if (e.getAttribute(a) === i.shown) e.setAttribute(a, i.orig);
    });
  }

  private async flush() {
    if (this.inflight || !this.pending.size || this.stopped) return;
    this.inflight = true;
    this.onBusy(true);
    try {
      while (this.pending.size && !this.stopped) {
        const batch: string[] = [];
        let chars = 0;
        for (const s of this.pending) {
          if (batch.length >= 50 || chars + s.length > 12000) break;
          batch.push(s); chars += s.length;
        }
        batch.forEach((s) => this.pending.delete(s));
        const res = await request<{ texts: string[] }>("/translate", { method: "POST", body: { lang: this.lang, texts: batch } });
        batch.forEach((s, i) => { if (res.texts[i]) this.cache.set(s, res.texts[i]); });
        writeCache(this.lang, this.cache);
        if (!this.stopped) this.scan(document.body);
      }
    } catch (e) {
      this.pending.clear();
      this.onError((e as Error).message || "Translation is unavailable.");
    } finally {
      this.inflight = false;
      this.onBusy(false);
    }
  }
}

export function LanguageProvider({ children }: { children: ReactNode }) {
  const { push } = useToast();
  const [lang, setLangState] = useState<string>(() => { try { return localStorage.getItem(LS_LANG) || DEFAULT_LANG; } catch { return DEFAULT_LANG; } });
  const [languages, setLanguages] = useState<Language[]>(FALLBACK_LANGS);
  const [configured, setConfigured] = useState<boolean | null>(null);
  const [busy, setBusy] = useState(false);
  const engine = useRef<Engine | null>(null);

  const setLang = useCallback((code: string) => {
    setLangState(code);
    try { localStorage.setItem(LS_LANG, code); } catch { /* preference only */ }
  }, []);

  // learn which languages the server offers (needs a session; falls back to the built-in list)
  useEffect(() => {
    let live = true;
    request<{ configured: boolean; languages: Language[] }>("/translate/languages").then((r) => { if (live) { setLanguages(r.languages); setConfigured(r.configured); } }).catch(() => undefined);
    return () => { live = false; };
  }, []);

  useEffect(() => {
    document.documentElement.lang = lang.split("-")[0];
    engine.current?.stop(true);
    engine.current = null;
    if (lang === DEFAULT_LANG) return;
    const e = new Engine(lang, (msg) => {
      push({ title: "Could not translate this page", description: msg, variant: "error" });
      setLang(DEFAULT_LANG);
    }, setBusy);
    engine.current = e;
    e.start();
    return () => { e.stop(false); };
  }, [lang, push, setLang]);

  const value = useMemo(() => ({ lang, setLang, languages, busy, configured }), [lang, setLang, languages, busy, configured]);
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}
