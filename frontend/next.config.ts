import path from "path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  turbopack: {
    root: process.cwd(),
  },
  webpack: (config) => {
    config.resolve.alias = {
      ...config.resolve.alias,
      "@": path.resolve(__dirname, "src"),
    };

    return config;
  },
  async rewrites() {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || '';
    const backendBase = apiUrl.startsWith('http')
      ? apiUrl
      : 'http://backend:8000/api';
    return {
      // fallback: 모든 route handler 체크 후 마지막에 적용 → 스트리밍 route handler가 완전 우선
      fallback: [
        {
          source: "/api/:path*",
          destination: `${backendBase}/:path*`,
        },
      ],
    };
  },
};

export default nextConfig;
