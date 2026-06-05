import type { NextConfig } from "next";

const parseAllowedOrigins = () => {
  const origins = process.env.ALLOWED_DEV_ORIGINS;
  if (!origins) return [];
  return origins.split(",").map(o => o.trim()).filter(Boolean);
};

const nextConfig: NextConfig = {
  /* config options here */
  allowedDevOrigins: [
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    ...parseAllowedOrigins()
  ],
};

export default nextConfig;


