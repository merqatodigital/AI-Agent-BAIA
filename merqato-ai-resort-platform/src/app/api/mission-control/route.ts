import { getDataStore, DEFAULT_RESORT_ID } from "@/lib/data";

export async function GET() {
  const store = getDataStore();
  const data = await store.getMissionControl(DEFAULT_RESORT_ID);
  return Response.json(data);
}
