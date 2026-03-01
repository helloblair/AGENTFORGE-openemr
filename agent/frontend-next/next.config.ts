import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Frame-Options", value: "ALLOWALL" },
          {
            key: "Content-Security-Policy",
            value:
              "frame-ancestors 'self' http://localhost:8300 https://localhost:9300 https://openemr-production-7df2.up.railway.app",
          },
        ],
      },
    ];
  },
};

export default nextConfig;
