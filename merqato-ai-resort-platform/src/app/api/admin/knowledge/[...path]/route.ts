import { NextRequest, NextResponse } from "next/server";
import { DEFAULT_TENANT_SLUG } from "@/lib/config";

/**
 * Admin BFF proxy to the FastAPI knowledge-management API.
 *
 * The browser talks ONLY to this route (protected by the admin middleware);
 * the shared server-to-server secret (ADMIN_API_TOKEN) is attached here,
 * server-side, and never shipped to the client. The tenant slug is pinned to
 * the canonical DEFAULT_TENANT_SLUG — the browser cannot choose a tenant.
 */

const AGENT_API_URL = process.env.AGENT_API_URL ?? "http://localhost:8000";

// Subpaths of the FastAPI knowledge API this proxy will forward. Anything
// else is rejected before leaving the BFF.
const ALLOWED = [
  /^categories$/,
  /^jobs$/,
  /^[a-z_]+\/(current|versions|audits)$/,
  /^[a-z_]+\/draft$/,
  /^versions\/[A-Za-z0-9-]+\/(verify|publish|unpublish)$/,
];

async function forward(
  req: NextRequest,
  params: Promise<{ path: string[] }>,
  method: "GET" | "POST",
) {
  const { path } = await params;
  const subpath = (path ?? []).join("/");
  if (!ALLOWED.some((p) => p.test(subpath))) {
    return NextResponse.json({ error: "unknown admin route" }, { status: 404 });
  }

  const token = process.env.ADMIN_API_TOKEN;
  if (!token) {
    // Fail closed: the admin knowledge API is disabled until configured.
    return NextResponse.json(
      { error: "admin knowledge API is not configured" },
      { status: 503 },
    );
  }

  const url = new URL(
    `${AGENT_API_URL}/v1/admin/tenants/${DEFAULT_TENANT_SLUG}/knowledge/${subpath}`,
  );
  req.nextUrl.searchParams.forEach((value, key) => {
    url.searchParams.set(key, value);
  });

  let upstream: Response;
  try {
    upstream = await fetch(url, {
      method,
      headers: {
        "Content-Type": "application/json",
        "X-Admin-Token": token,
      },
      body: method === "POST" ? await req.text() : undefined,
      signal: AbortSignal.timeout(60_000),
    });
  } catch {
    return NextResponse.json(
      { error: "knowledge service unreachable" },
      { status: 502 },
    );
  }

  const data = await upstream.json().catch(() => null);
  return NextResponse.json(data ?? { error: "invalid upstream response" }, {
    status: upstream.status,
  });
}

export async function GET(
  req: NextRequest,
  ctx: { params: Promise<{ path: string[] }> },
) {
  return forward(req, ctx.params, "GET");
}

export async function POST(
  req: NextRequest,
  ctx: { params: Promise<{ path: string[] }> },
) {
  return forward(req, ctx.params, "POST");
}
