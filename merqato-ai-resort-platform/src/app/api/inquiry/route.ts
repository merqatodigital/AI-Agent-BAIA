import { NextRequest } from "next/server";
import { getDataStore, DEFAULT_RESORT_ID } from "@/lib/data";

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => null);
  if (!body?.name || !body?.email || !body?.message) {
    return Response.json(
      { error: "name, email and message are required" },
      { status: 400 },
    );
  }
  const store = getDataStore();
  const inquiry = await store.createInquiry(DEFAULT_RESORT_ID, {
    name: String(body.name),
    email: String(body.email),
    message: String(body.message),
    checkIn: body.checkIn ? String(body.checkIn) : undefined,
    checkOut: body.checkOut ? String(body.checkOut) : undefined,
    guests: body.guests ? Number(body.guests) : undefined,
  });
  return Response.json({ ok: true, inquiry }, { status: 201 });
}
