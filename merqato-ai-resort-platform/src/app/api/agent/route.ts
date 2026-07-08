import { NextRequest, NextResponse } from "next/server";
import { DEFAULT_TENANT_SLUG } from "@/lib/config";

/**
 * BFF proxy to the FastAPI agent service (services/agent-api).
 *
 * This route does NOT contain any agent logic. It forwards the guest's
 * message to FastAPI's real CrewAI concierge endpoint and returns the FastAPI
 * response contract unchanged. The single production agent engine is
 * FastAPI + the actual CrewAI framework; this file is only a thin proxy.
 *
 * FastAPI base URL is read from AGENT_API_URL (default http://localhost:8000).
 * No secrets (OpenRouter keys) are read or forwarded here.
 */

const AGENT_API_URL = process.env.AGENT_API_URL ?? "http://localhost:8000";

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => null);
  const message = body?.message as string | undefined;
  const resortId = (body?.resortId as string | undefined) ?? DEFAULT_TENANT_SLUG;
  const locale = (body?.locale as string | undefined) ?? "en";
  const conversationId =
    (body?.conversationId as string | undefined) ?? crypto.randomUUID();

  if (!message || !message.trim()) {
    return NextResponse.json({ error: "message required" }, { status: 400 });
  }

  let upstream: Response;
  try {
    upstream = await fetch(`${AGENT_API_URL}/v1/concierge/message`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        resort_id: resortId,
        conversation_id: conversationId,
        message,
        locale,
      }),
      // Do not hang the request indefinitely.
      signal: AbortSignal.timeout(60_000),
    });
  } catch {
    // Network failure / FastAPI unreachable: controlled error, no fabrication.
    return NextResponse.json(
      {
        reply:
          "I'm having trouble connecting to the concierge service. Please try again shortly.",
        intent: "service_unavailable",
        confidence: 0,
        sources: [],
        proposed_actions: [],
        requires_approval: false,
        escalation_reason: "agent_api_unreachable",
      },
      { status: 502 },
    );
  }

  // Forward FastAPI's status and body unchanged. FastAPI returns a controlled
  // 503 when OpenRouter is not configured (no fabricated answer, no secrets).
  const data = await upstream.json().catch(() => null);
  return NextResponse.json(data ?? { error: "invalid agent response" }, {
    status: upstream.status,
  });
}
