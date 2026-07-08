import { NextRequest, NextResponse } from "next/server";

/**
 * BFF proxy to the FastAPI agent service's OpenRouter key validation.
 *
 * This route contains NO direct OpenRouter network call and NO model-execution
 * logic. It forwards the customer's key (transient, never stored) to FastAPI's
 * POST /v1/openrouter/validate, which owns all OpenRouter communication.
 *
 * FastAPI base URL comes from AGENT_API_URL (default http://localhost:8000).
 * The API key is forwarded to FastAPI only and is never logged here.
 */

const AGENT_API_URL = process.env.AGENT_API_URL ?? "http://localhost:8000";

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => null);
  const apiKey = body?.api_key as string | undefined;
  const model = body?.model as string | undefined;

  if (!apiKey || typeof apiKey !== "string") {
    return NextResponse.json({ error: "api_key required" }, { status: 400 });
  }

  let upstream: Response;
  try {
    upstream = await fetch(`${AGENT_API_URL}/v1/openrouter/validate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ api_key: apiKey, model }),
      signal: AbortSignal.timeout(30_000),
    });
  } catch {
    // FastAPI unreachable: controlled error, no key logging.
    return NextResponse.json(
      { valid: false, message: "Concierge service unreachable." },
      { status: 502 },
    );
  }

  const data = await upstream.json().catch(() => null);
  return NextResponse.json(data ?? { valid: false, message: "Bad response" }, {
    status: upstream.status,
  });
}
