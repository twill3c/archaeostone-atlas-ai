/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // SPEC N-02: 静的配信のみ(Vercel Function 0 個)。
  // 出荷形を out/ にすることで、実ブラウザ検品も素の静的サーバで行える。
  output: "export",
  images: { unoptimized: true },
  trailingSlash: true,
};

export default nextConfig;
