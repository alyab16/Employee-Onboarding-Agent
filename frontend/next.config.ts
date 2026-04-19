import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Emit a minimal self-contained server under `.next/standalone` — used by
  // the production Docker image so we don't have to ship node_modules.
  output: "standalone",
};

export default nextConfig;
