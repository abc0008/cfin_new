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
};

module.exports = nextConfig;