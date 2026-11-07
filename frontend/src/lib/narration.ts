/**
 * Optional spoken narration, powered by Sarvam AI through the backend.
 *
 *  - the provider key stays on the server; the browser only ever asks for audio;
 *  - the control is hidden unless the server reports narration as configured;
 *  - audio is fetched in whatever language the student has chosen for the
 *    interface, because the backend translates before it speaks;
 *  - each distinct piece of text is fetched once per session and reused.
 *
 * Nothing else in the app depends on this: when it is unavailable, callers get
 * `available === false` and simply render no control.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { requestBlob, request } from "./api";
import { useI18n } from "./i18n";

const LS_AUTOPLAY = "arjuna.narration.autoplay";

export type NarrationState = "idle" | "loading" | "playing" | "error";

/** One cache for the whole tab, keyed by language and text. */
const audioCache = new Map<string, string>();

/** Server capability, fetched once per tab. */
let statusPromise: Promise<boolean> | null = null;
function fetchStatus(): Promise<boolean> {
  if (!statusPromise) {
    statusPromise = request<{ configured: boolean }>("/narration/status")
      .then((d) => !!d?.configured)
      .catch(() => false);
  }
  return statusPromise;
}

function readAutoplay(): boolean {
  try {
    return localStorage.getItem(LS_AUTOPLAY) === "on";
  } catch {
    return false;
  }
}

export function useNarration() {
  const { lang } = useI18n();
  const [available, setAvailable] = useState<boolean | null>(null);
  const [state, setState] = useState<NarrationState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [autoplay, setAutoplayState] = useState(readAutoplay);

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const tokenRef = useRef(0);

  useEffect(() => {
    let alive = true;
    fetchStatus().then((ok) => alive && setAvailable(ok));
    return () => {
      alive = false;
    };
  }, []);

  // one audio element for the whole hook
  useEffect(() => {
    const el = new Audio();
    el.preload = "auto";
    audioRef.current = el;
    return () => {
      el.pause();
      el.src = "";
      audioRef.current = null;
    };
  }, []);

  const stop = useCallback(() => {
    tokenRef.current += 1; // cancels any in-flight fetch
    const el = audioRef.current;
    if (el) {
      el.pause();
      el.currentTime = 0;
    }
    setState("idle");
  }, []);

  const setAutoplay = useCallback(
    (on: boolean) => {
      setAutoplayState(on);
      try {
        localStorage.setItem(LS_AUTOPLAY, on ? "on" : "off");
      } catch {
        /* storage blocked: the choice just will not persist */
      }
      if (!on) stop();
    },
    [stop]
  );

  const play = useCallback(
    async (text: string) => {
      const clean = text?.trim();
      if (!clean) return;

      const token = ++tokenRef.current;
      const key = `${lang}\u001f${clean}`;
      setError(null);
      setState("loading");

      try {
        let url = audioCache.get(key);
        if (!url) {
          const blob = await requestBlob("/narration", { method: "POST", body: { text: clean, lang } });
          if (token !== tokenRef.current) return; // superseded or stopped
          url = URL.createObjectURL(blob);
          audioCache.set(key, url);
        }

        const el = audioRef.current;
        if (!el || token !== tokenRef.current) return;

        el.pause();
        el.src = url;
        el.onended = () => {
          if (token === tokenRef.current) setState("idle");
        };
        el.onerror = () => {
          if (token === tokenRef.current) {
            setError("This narration could not be played.");
            setState("error");
          }
        };
        await el.play();
        if (token === tokenRef.current) setState("playing");
      } catch (e) {
        if (token !== tokenRef.current) return;
        const name = (e as Error)?.name;
        if (name === "AbortError" || name === "NotAllowedError") {
          // the browser blocked autoplay, or we were cancelled — not worth an error
          setState("idle");
          return;
        }
        setError((e as Error)?.message ?? "Narration is unavailable right now.");
        setState("error");
      }
    },
    [lang]
  );

  // a language change invalidates whatever is currently playing
  useEffect(() => {
    stop();
  }, [lang, stop]);

  return { available, state, error, play, stop, autoplay, setAutoplay };
}
