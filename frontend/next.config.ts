import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Emit a self-contained server (.next/standalone) with only the
  // node_modules it actually uses, so the Docker image doesn't ship the
  // whole dev toolchain. `npm run dev` and `npm run build` are unaffected.
  output: "standalone",
};

export default nextConfig;
