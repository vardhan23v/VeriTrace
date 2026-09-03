/** @type {import('next').NextConfig} */
const nextConfig = {
  // no static export — we need /api/search on Vercel
  images: { unoptimized: true }
};
module.exports = nextConfig;
