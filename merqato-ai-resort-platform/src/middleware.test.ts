import { describe, test, expect, afterEach } from "vitest";
import { NextRequest } from "next/server";
import { middleware } from "./middleware";

function makeReq(pathname: string, auth?: string): NextRequest {
  const headers = new Headers();
  if (auth) headers.set("authorization", auth);
  const url = new URL(`http://localhost:3000${pathname}`);
  return new NextRequest(url, { headers });
}

const BASIC = "Basic " + Buffer.from("admin:secret").toString("base64");

describe("temporary admin Basic Auth middleware", () => {
  const origEnv = process.env;

  afterEach(() => {
    process.env = origEnv;
  });

  test("public concierge page is not protected", async () => {
    process.env = { ...origEnv };
    const res = await middleware(makeReq("/concierge"));
    expect(res.status).toBe(200);
  });

  test("public inquiry API is not protected", async () => {
    process.env = { ...origEnv };
    const res = await middleware(makeReq("/api/inquiry"));
    expect(res.status).toBe(200);
  });

  test("admin page denied without credentials (prod, missing env)", async () => {
    process.env = { ...origEnv, NODE_ENV: "production" };
    delete process.env.TEMP_ADMIN_USERNAME;
    delete process.env.TEMP_ADMIN_PASSWORD;
    const res = await middleware(makeReq("/admin"));
    expect(res.status).toBe(401);
  });

  test("protected API denied without Authorization header", async () => {
    process.env = {
      ...origEnv,
      TEMP_ADMIN_USERNAME: "admin",
      TEMP_ADMIN_PASSWORD: "secret",
    };
    const res = await middleware(makeReq("/api/mission-control"));
    expect(res.status).toBe(401);
    expect(res.headers.get("WWW-Authenticate")).toContain("Basic");
  });

  test("valid credentials are accepted", async () => {
    process.env = {
      ...origEnv,
      TEMP_ADMIN_USERNAME: "admin",
      TEMP_ADMIN_PASSWORD: "secret",
    };
    const res = await middleware(makeReq("/admin", BASIC));
    expect(res.status).toBe(200);
  });

  test("invalid credentials are rejected", async () => {
    process.env = {
      ...origEnv,
      TEMP_ADMIN_USERNAME: "admin",
      TEMP_ADMIN_PASSWORD: "secret",
    };
    const bad = "Basic " + Buffer.from("admin:wrong").toString("base64");
    const res = await middleware(makeReq("/api/resort", bad));
    expect(res.status).toBe(401);
  });
});
