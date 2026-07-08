import { isSupabaseConfigured } from "../config";
import type { DataStore } from "./store";
import { DevDataStore } from "./dev-store";
import { createSupabaseStore } from "./supabase-store";

/**
 * Returns the active DataStore for the environment.
 * - Supabase when NEXT_PUBLIC_SUPABASE_URL + key are present
 * - Dev (seeded in-memory) otherwise, so the product runs with zero config.
 *
 * A single shared instance keeps the dev adapter stateful across requests in
 * dev (acceptable for demo; Supabase is stateless by nature).
 */
let cached: DataStore | null = null;

export function getDataStore(): DataStore {
  if (cached) return cached;
  cached = isSupabaseConfigured() ? createSupabaseStore() : new DevDataStore();
  return cached;
}

export const DEFAULT_RESORT_ID = "resort_demo";
