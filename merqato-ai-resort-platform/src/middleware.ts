import { NextRequest, NextResponse } from "next/server";

/**
 * TEMPORARY server-side Basic Auth gate for owner/admin surfaces.
 *
 * This is an interim control ONLY and will be replaced by Supabase Auth in a
 * later milestone. It is intentionally minimal: a single shared username/
 * password read from the environment, applied to admin pages and the admin
 * API routes. Guest surfaces (/, /concierge, /api/agent, /api/inquiry) are
 * NOT protected.
 *
 * Fail-closed: if the credentials are not configured and we are not in
 * development, all protected routes are denied.
 */

const PROTECTED_PREFIXES = [
  "/admin",
  "/api/admin",
  "/api/mission-control",
  "/api/resort",
  "/api/openrouter",
];

function isProtected(pathname: string): boolean {
  return PROTECTED_PREFIXES.some(
    (p) => pathname === p || pathname.startsWith(`${p}/`),
  );
}

function unauthorized() {
  return new NextResponse("Unauthorized", {
    status: 401,
    headers: { "WWW-Authenticate": 'Basic realm="MerQato Admin"' },
  });
}

export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;

  if (!isProtected(pathname)) {
    return NextResponse.next();
  }

  const username = process.env.TEMP_ADMIN_USERNAME;
  const password = process.env.TEMP_ADMIN_PASSWORD;
  const isProd = process.env.NODE_ENV === "production";

  // Fail closed when credentials are missing (always in production).
  if (!username || !password) {
    if (isProd) return unauthorized();
    // In development, allow access without the guard to keep local DX simple.
    return NextResponse.next();
  }

  const header = req.headers.get("authorization");
  if (!header?.startsWith("Basic ")) {
    return unauthorized();
  }

  const decoded = Buffer.from(header.slice(6), "base64").toString("utf-8");
  const [u, p] = decoded.split(":");
  if (u === username && p === password) {
    return NextResponse.next();
  }
  return unauthorized();
}

export const config = {
  // Do not match the explicitly public routes; guard only the listed prefixes.
  matcher: [
    "/admin/:path*",
    "/api/admin/:path*",
    "/api/mission-control/:path*",
    "/api/resort/:path*",
    "/api/openrouter/:path*",
  ],
};
