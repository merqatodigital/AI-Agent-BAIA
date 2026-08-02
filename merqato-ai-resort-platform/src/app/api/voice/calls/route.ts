const VOICE_API_URL = process.env.VOICE_API_URL ?? "http://localhost:8765";

export async function POST(request: Request) {
  if (!request.headers.get("content-type")?.includes("application/sdp")) {
    return new Response("Content-Type must be application/sdp", { status: 415 });
  }

  let upstream: Response;
  try {
    upstream = await fetch(`${VOICE_API_URL}/v1/realtime/calls`, {
      method: "POST",
      headers: { "Content-Type": "application/sdp" },
      body: await request.text(),
      signal: AbortSignal.timeout(30_000),
    });
  } catch {
    return Response.json(
      { error: "TALA voice service is unavailable" },
      { status: 502 },
    );
  }

  const body = await upstream.text();
  const headers = new Headers({
    "Content-Type":
      upstream.headers.get("content-type") ?? "application/sdp",
  });
  const location = upstream.headers.get("location");
  if (location) {
    const callId = location.split("/").filter(Boolean).at(-1);
    if (callId) headers.set("Location", `/api/voice/calls/${callId}`);
  }
  return new Response(body, { status: upstream.status, headers });
}
