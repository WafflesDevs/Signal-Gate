/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_SUPABASE_URL: string;
  readonly VITE_SUPABASE_ANON_KEY: string;
  /** Preferred API origin override (empty = same-origin / Vite proxy). */
  readonly VITE_API_BASE?: string;
  /** Alias for VITE_API_BASE. */
  readonly VITE_API_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
