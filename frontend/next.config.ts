import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Two build targets from one config:
  //
  //   standalone (default) — a minimal self-contained server under
  //     `.next/standalone`, used by frontend/Dockerfile and docker-compose.
  //   export (NEXT_OUTPUT=export) — plain HTML/JS/CSS in `out/`, used by the
  //     AWS deployment. Every component here is a client component and there
  //     are no route handlers, so there is nothing for a server to do; S3 plus
  //     CloudFront serves it with no Node runtime to pay for or patch.
  output: process.env.NEXT_OUTPUT === "export" ? "export" : "standalone",

  // A static export has no image optimisation server.
  images: { unoptimized: true },
};

export default nextConfig;
