import { NextRequest } from "next/server";
import { getDataStore, DEFAULT_RESORT_ID } from "@/lib/data";
import type { ResortProfile } from "@/lib/types";

export async function PATCH(req: NextRequest) {
  const body = (await req.json().catch(() => null)) as
    | Partial<ResortProfile>
    | null;
  if (!body) return Response.json({ error: "body required" }, { status: 400 });
  const store = getDataStore();
  const updated = await store.updateResortProfile(DEFAULT_RESORT_ID, body);
  return Response.json({ ok: true, profile: updated });
}
