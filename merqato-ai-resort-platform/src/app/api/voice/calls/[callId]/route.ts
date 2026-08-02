const VOICE_API_URL = process.env.VOICE_API_URL ?? "http://localhost:8765";

export async function DELETE(
  _request: Request,
  { params }: { params: Promise<{ callId: string }> },
) {
  const { callId } = await params;
  let upstream: Response;
  try {
    upstream = await fetch(
      `${VOICE_API_URL}/v1/realtime/calls/${encodeURIComponent(callId)}`,
      { method: "DELETE", signal: AbortSignal.timeout(10_000) },
    );
  } catch {
    return Response.json(
      { error: "TALA voice service is unavailable" },
      { status: 502 },
    );
  }
  return new Response(await upstream.text(), { status: upstream.status });
}
