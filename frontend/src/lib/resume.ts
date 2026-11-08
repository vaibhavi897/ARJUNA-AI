/** Typed client for the Dynamic Resume Builder. */
import { API_BASE, ApiError, getToken, request } from "./api";

export type Entry = { title: string; right: string; subtitle: string; subright: string; bullets: string[]; source?: { ref?: string } };
export type Line = { label: string; text: string };
export type Section = { key: string; title: string; type: "entries" | "bullets" | "lines"; entries?: Entry[]; bullets?: string[]; lines?: Line[]; refs?: string[] };
export type Content = { header: { name: string; contacts: string[] }; sections: Section[] };
export type Fit = { fits: boolean; scale: number; overflow_lines: number; last_baseline: number; limit: number; shrunk: boolean };
export type Included = { ref: string; kind: string; title: string; org: string; score: number; reasons: string[]; matched: string[]; flags: string[]; source: string | null };
export type Version = {
  id: number; title: string; job_title: string; company: string | null; role_type: string; edited: boolean; created_at: string | null; updated_at: string | null;
  job_description?: string | null;
  analysis?: { role_type: string; keywords: string[]; emphasis: string[]; seniority: string; source: string; inferred?: boolean };
  content?: Content;
  selection?: { included: Included[]; excluded: Included[]; trimmed_for_space: string[]; keywords_found: string[]; keywords_missing: string[]; ai_tailored: boolean };
  fit?: Fit; ai_available?: boolean;
};
export type Candidate = { ref: string; kind: string; title: string; org: string; score: number; reasons: string[]; included: boolean };

const base = "/resume-builder";
export const rb = {
  check: () => request<{ ready: boolean; education: number; skills: number; counts: Record<string, number>; ai_available: boolean }>(`${base}/profile-check`),
  list: () => request<Version[]>(`${base}/versions`),
  get: (id: number) => request<Version>(`${base}/versions/${id}`),
  generate: (body: { job_title: string; company?: string; job_description?: string }) => request<Version>(`${base}/generate`, { method: "POST", body }),
  save: (id: number, content: Content, title?: string) => request<Version>(`${base}/versions/${id}`, { method: "PUT", body: { content, title } }),
  fit: (content: Content) => request<Fit>(`${base}/fit`, { method: "POST", body: { content } }),
  regenerate: (id: number) => request<Version>(`${base}/versions/${id}/regenerate`, { method: "POST" }),
  candidates: (id: number) => request<Candidate[]>(`${base}/versions/${id}/candidates`),
  swap: (id: number, add_ref: string, remove_ref?: string | null) => request<Version>(`${base}/versions/${id}/swap`, { method: "POST", body: { add_ref, remove_ref } }),
  remove: (id: number) => request<void>(`${base}/versions/${id}`, { method: "DELETE" }),
};

async function blobOf(path: string, init: RequestInit = {}): Promise<{ blob: Blob; filename: string | null }> {
  const token = getToken();
  const res = await fetch(`${API_BASE}${base}${path}`, { ...init, headers: { ...(init.headers || {}), ...(token ? { Authorization: `Bearer ${token}` } : {}), ...(init.body ? { "Content-Type": "application/json" } : {}) } });
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try { const j = await res.json(); if (typeof j?.detail === "string") detail = j.detail; } catch { /* keep default */ }
    throw new ApiError(res.status, detail);
  }
  const m = /filename="([^"]+)"/.exec(res.headers.get("content-disposition") || "");
  return { blob: await res.blob(), filename: m ? m[1] : null };
}

/** Render the (possibly unsaved) editor content with the exact exporter. */
export const previewPdf = (content: Content, signal?: AbortSignal) => blobOf("/preview", { method: "POST", body: JSON.stringify({ content }), signal }).then((r) => r.blob);

export async function download(id: number, kind: "pdf" | "docx"): Promise<void> {
  const { blob, filename } = await blobOf(`/versions/${id}/${kind}`);
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename || `resume.${kind}`;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}
