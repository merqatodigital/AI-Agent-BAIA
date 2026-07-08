/**
 * Central configuration. Client-safe values are exposed via NEXT_PUBLIC_*.
 * Server-only secrets are read lazily inside server modules (route handlers,
 * server components) and are never shipped to the browser.
 */

/**
 * Canonical tenant slug for the BAIA resort. The same value is used by the
 * FastAPI agent service (app/config.py DEFAULT_TENANT_SLUG), Supabase seeds
 * and Qdrant collection naming. Keep in sync — never scatter slug literals.
 */
export const DEFAULT_TENANT_SLUG = "baia-resort";

export const clientEnv = {
  supabaseUrl: process.env.NEXT_PUBLIC_SUPABASE_URL ?? "",
  supabaseAnonKey: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "",
  appUrl: process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000",
};

/** Server-only secret access. Only call from server context. */
export const serverEnv = {
  supabaseUrl: process.env.NEXT_PUBLIC_SUPABASE_URL ?? "",
  supabaseServiceRole: process.env.SUPABASE_SERVICE_ROLE_KEY ?? "",
  supabaseAnonKey: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "",
  openRouterKey: process.env.OPENROUTER_API_KEY ?? "",
  openRouterBaseUrl:
    process.env.OPENROUTER_BASE_URL ?? "https://openrouter.ai/api/v1",
  openRouterModel: process.env.OPENROUTER_MODEL ?? "openai/gpt-4o-mini",
};

export function isSupabaseConfigured(): boolean {
  return Boolean(
    (clientEnv.supabaseUrl || serverEnv.supabaseUrl) &&
      (clientEnv.supabaseAnonKey ||
        serverEnv.supabaseServiceRole ||
        serverEnv.supabaseAnonKey),
  );
}

export function isOpenRouterConfigured(): boolean {
  return Boolean(serverEnv.openRouterKey);
}
