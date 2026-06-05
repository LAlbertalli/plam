import type { NextConfig } from "next";

const parseAllowedOrigins = () => {
  const origins = process.env.ALLOWED_DEV_ORIGINS;
  if (!origins) return [];
  const list = origins.split(",").map(o => o.trim()).filter(Boolean);
  const port = process.env.PORT || "3000";
  // Add both IP-only and IP:port combinations for robustness
  const withPorts = list.map(o => o.includes(":") ? o : `${o}:${port}`);
  return [...list, ...withPorts];
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


