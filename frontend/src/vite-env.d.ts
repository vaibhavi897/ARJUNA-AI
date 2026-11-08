/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Backend address ending in /api, set at build time for production. Empty in development. */
  readonly VITE_API_BASE?: string;
}
interface ImportMeta {
  readonly env: ImportMetaEnv;
}
