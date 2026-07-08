import { defineConfig } from "vitest/config";
import path from "node:path";

export default defineConfig({
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
  },
  test: {
    environment: "node",
    include: ["src/**/*.test.ts"],
    // No frontend unit tests remain after the TS agent engine was removed;
    // the agent logic now lives in the FastAPI service. Don't fail when empty.
    passWithNoTests: true,
  },
});
