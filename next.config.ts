import type { NextConfig } from "next";

const nextConfig: NextConfig = {  // Enable standalone output for Docker
  output: 'standalone',
  
  // Allow images from external sources if needed
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '**',
      },
    ],
  },
  
  // Environment variables for runtime
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1',
    NEXT_PUBLIC_MAX_UPLOAD_FILES: process.env.NEXT_PUBLIC_MAX_UPLOAD_FILES || '10',
    NEXT_PUBLIC_MAX_FILE_SIZE_MB: process.env.NEXT_PUBLIC_MAX_FILE_SIZE_MB || '4',
  },
};

export default nextConfig;
