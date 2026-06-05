const { loadEnvConfig } = require('@next/env');
loadEnvConfig(process.cwd());

const { createServer } = require('http');
const { parse } = require('url');
const next = require('next');
const HttpProxy = require('http-proxy');

const dev = process.env.NODE_ENV !== 'production';
const args = process.argv.slice(2);
let hostname = '0.0.0.0';
let port = parseInt(process.env.PORT, 10) || 3000;

for (let i = 0; i < args.length; i++) {
  if (args[i] === '-H' || args[i] === '--hostname') {
    hostname = args[i + 1] || hostname;
  } else if (args[i] === '-p' || args[i] === '--port') {
    port = parseInt(args[i + 1], 10) || port;
  }
}

const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const app = next({ dev, hostname, port });
const handle = app.getRequestHandler();

const proxy = HttpProxy.createProxyServer({
  target: backendUrl,
  ws: true,
});

app.prepare().then(() => {
  const server = createServer((req, res) => {
    const parsedUrl = parse(req.url, true);
    const { pathname } = parsedUrl;

    if (pathname.startsWith('/api')) {
      // Proxy API requests to backend
      proxy.web(req, res, {}, (err) => {
        console.error('API proxy error:', err);
        if (!res.headersSent) {
          res.statusCode = 500;
          res.end('Proxy error');
        }
      });
    } else {
      handle(req, res, parsedUrl);
    }
  });

  // Handle WebSocket upgrades
  server.on('upgrade', (req, socket, head) => {
    const parsedUrl = parse(req.url, true);
    const { pathname } = parsedUrl;

    if (pathname.startsWith('/api')) {
      // Proxy our backend websockets
      proxy.ws(req, socket, head, {}, (err) => {
        console.error('WebSocket proxy error:', err);
        socket.destroy();
      });
    } else if (pathname === '/_next/webpack-hmr' || pathname.startsWith('/_nextjs/websocket')) {
      // Pass HMR websockets to Next.js upgrade handler
      const upgradeHandler = app.getUpgradeHandler();
      if (upgradeHandler) {
        upgradeHandler(req, socket, head);
      } else {
        socket.destroy();
      }
    } else {
      socket.destroy();
    }
  });

  server.listen(port, hostname, (err) => {
    if (err) throw err;
    console.log(`> Ready on http://${hostname}:${port}`);
  });
});
