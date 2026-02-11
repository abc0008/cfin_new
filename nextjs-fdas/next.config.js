/** @type {import('next').NextConfig} */
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
  experimental: {
    // Force SWC transform
    forceSwcTransforms: true,
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
    ];
  },

  async rewrites() {
    return [
      {
        source: "/api/citations/:path*",
        destination: "http://localhost:8000/api/citations/:path*",
      },
    ];
  },
};

module.exports = nextConfig;