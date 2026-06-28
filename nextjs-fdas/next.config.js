/** @type {import('next').NextConfig} */
const rawBackendApiUrl =
  process.env.NEXT_PUBLIC_API_URL ||
  process.env.API_BASE_URL ||
  "https://cfin-backend.vercel.app";
const backendApiBaseUrl = rawBackendApiUrl.replace(/\/+$/, "").replace(/\/api$/, "");

const nextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: 'http',
        hostname: 'localhost',
        port: '',
        pathname: '/**',
      },
    ],
  },
  // Explicitly enable SWC
  swcMinify: true,
  eslint: {
    ignoreDuringBuilds: true,
  },
  webpack: (config) => {
    // Support loading PDF files
    config.module.rules.push({
      test: /\.pdf$/,
      use: [
        {
          loader: 'file-loader',
          options: {
            name: '[path][name].[ext]',
          },
        },
      ],
    });
    return config;
  },
  // For PDF Highlighter compatibility
  transpilePackages: ["react-pdf-highlighter"],

  async redirects() {
    return [
      {
        source: "/:path*",
        has: [{ type: "host", value: "www.aceanalytics.dev" }],
        destination: "https://aceanalytics.dev/:path*",
        permanent: true,
      },
      {
        source: "/",
        has: [{ type: "host", value: "fdas.aceanalytics.dev" }],
        destination: "/workspace",
        permanent: false,
      },
      {
        source: "/text2sql",
        destination: "https://text2sql.aceanalytics.dev",
        permanent: false,
      },
      {
        source: "/text2sql/:path*",
        destination: "https://text2sql.aceanalytics.dev/:path*",
        permanent: false,
      },
      {
        source: "/text2SQL",
        destination: "https://text2sql.aceanalytics.dev",
        permanent: false,
      },
      {
        source: "/text2SQL/:path*",
        destination: "https://text2sql.aceanalytics.dev/:path*",
        permanent: false,
      },
      {
        source: "/cfin",
        destination: "/product/cfin",
        permanent: false,
      },
      {
        source: "/rm",
        destination: "/product/lattice",
        permanent: false,
      },
      {
        source: "/product/rm",
        destination: "/product/lattice",
        permanent: false,
      },
      {
        source: "/credit-spread",
        destination: "/product/credit-spread",
        permanent: false,
      },
      {
        source: "/forecasting",
        destination: "/product/forecasting",
        permanent: false,
      },
      {
        source: "/forecasting/app",
        destination: "https://bankanalysis.aceanalytics.dev/forecasting",
        permanent: false,
      },
      {
        source: "/lattice",
        destination: "/product/lattice",
        permanent: false,
      },
      {
        source: "/peer-analysis",
        destination: "/product/peer-analysis",
        permanent: false,
      },
      {
        source: "/peer-lens",
        destination: "/product/peer-analysis",
        permanent: false,
      },
    ];
  },

  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${backendApiBaseUrl}/api/:path*`,
      },
      {
        source: "/ws/:path*",
        destination: `${backendApiBaseUrl}/ws/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
