import { createClient } from "@supabase/supabase-js";

const url = import.meta.env.VITE_SUPABASE_URL as string | undefined;
const anon = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined;

if (!url || !anon) {
  // Vite embeds VITE_* at build time. Never fall back to localhost — that
  // produces "Failed to fetch" / ERR_CONNECTION_REFUSED on Render when the
  // build ran without these env vars.
  throw new Error(
    "Missing VITE_SUPABASE_URL or VITE_SUPABASE_ANON_KEY. " +
      "Set them in frontend/.env for local dev, or in Render Environment " +
      "(same values as SUPABASE_URL / SUPABASE_ANON_KEY) and redeploy with a " +
      "clear build cache so Vite rebuilds with those vars."
  );
}

export const supabase = createClient(url, anon);
