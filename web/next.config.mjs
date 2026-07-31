/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Every page is generated from JSON committed in the repo, so there is nothing to
  // revalidate at runtime and no server-side data fetching anywhere in the app.
  images: {
    remotePatterns: [{ protocol: "https", hostname: "cdn.nba.com" }],
  },
};

export default nextConfig;
