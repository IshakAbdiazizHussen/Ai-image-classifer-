import path from "node:path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Pin the workspace root explicitly — without it, Next.js/Turbopack
  // walks up looking for a lockfile and can land on an unrelated one
  // elsewhere on disk (e.g. a parent directory outside this project).
  turbopack: {
    root: path.resolve(__dirname),
  },
};

export default nextConfig;
