import { NextRequest, NextResponse } from "next/server";
import { DEFAULT_TENANT_SLUG } from "@/lib/config";

const AGENT_API_URL = process.env.AGENT_API_URL ?? "http://localhost:8000";

async function forward(
  req: NextRequest,
  method: "GET" | "PUT" | "POST" | "DELETE",
) {
  const token = process.env.ADMIN_API_TOKEN;
  if (!token) {
    return NextResponse.json(
      { error: "admin provider API is not configured" },
      { status: 503 },
    );
  }

  const body = method === "GET" ? null : await req.json().catch(() => null);
  const action = body?.action as string | undefined;
  const suffix =
    method === "POST" && action === "detect_ollama"
      ? "/ollama/detect"
      : method === "DELETE"
        ? "/openrouter-key"
        : "";

  let upstream: Response;
  try {
    upstream = await fetch(
      `${AGENT_API_URL}/v1/admin/tenants/${DEFAULT_TENANT_SLUG}/ai-provider${suffix}`,
      {
        method,
        headers: {
          "Content-Type": "application/json",
          "X-Admin-Token": token,
        },
        body:
          method === "GET" || method === "DELETE"
            ? undefined
            : JSON.stringify(
                action === "detect_ollama"
                  ? { base_url: body?.base_url }
                  : body,
              ),
        signal: AbortSignal.timeout(30_000),
      },
    );
  } catch {
    return NextResponse.json(
      { error: "AI provider service unreachable" },
      { status: 502 },
    );
  }

  const data = await upstream.json().catch(() => null);
  return NextResponse.json(data ?? { error: "invalid upstream response" }, {
    status: upstream.status,
  });
}

export async function GET(req: NextRequest) {
  return forward(req, "GET");
}

export async function PUT(req: NextRequest) {
  return forward(req, "PUT");
}

export async function POST(req: NextRequest) {
  return forward(req, "POST");
}

export async function DELETE(req: NextRequest) {
  return forward(req, "DELETE");
}
