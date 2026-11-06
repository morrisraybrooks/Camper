#!/usr/bin/env python3
"""Camper Brain chat page -> Home Assistant MCP relay (2026-10-16).

Listens on 127.0.0.1 only and forwards /api/mcp to Home Assistant, adding the
long-lived token from /home/morris/.config/ha-mcp-token so the chat page never
needs the key. Only /api/mcp is passed through (Assist tools = what voice can do).
"""
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HA_HOST, HA_PORT, PATH = "192.168.0.168", 8123, "/api/mcp"
LISTEN = ("127.0.0.1", 8124)
TOKEN = open("/home/morris/.config/ha-mcp-token").read().strip()
PASS_REQ = ("content-type", "accept", "mcp-session-id", "mcp-protocol-version", "last-event-id")
SKIP_RESP = ("transfer-encoding", "connection", "content-length", "content-encoding")


class Relay(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _forward(self):
        if self.path.split("?")[0] != PATH:
            self.send_error(404, "Only /api/mcp is relayed")
            return
        body = self.rfile.read(int(self.headers.get("Content-Length") or 0)) or None
        headers = {k: v for k, v in self.headers.items() if k.lower() in PASS_REQ}
        headers["Authorization"] = "Bearer " + TOKEN
        conn = http.client.HTTPConnection(HA_HOST, HA_PORT, timeout=120)
        started = False  # once the response has begun, a 502 can't be sent any more
        try:
            conn.request(self.command, self.path, body=body, headers=headers)
            resp = conn.getresponse()
            self.send_response(resp.status, resp.reason)
            started = True
            for k, v in resp.getheaders():
                if k.lower() not in SKIP_RESP:
                    self.send_header(k, v)
            # Stream the body (SSE responses arrive in pieces)
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()
            while True:
                chunk = resp.read1(65536) if hasattr(resp, "read1") else resp.read(65536)
                if not chunk:
                    break
                self.wfile.write(b"%x\r\n%s\r\n" % (len(chunk), chunk))
                self.wfile.flush()
            self.wfile.write(b"0\r\n\r\n")
        except Exception as e:
            if started:
                # HA dropped mid-stream: just end the connection.
                self.close_connection = True
                return
            try:
                self.send_error(502, f"Home Assistant unreachable: {e}")
            except Exception:
                pass
        finally:
            conn.close()

    do_POST = do_GET = do_DELETE = _forward

    def log_message(self, fmt, *args):
        pass  # keep the journal quiet; errors still surface as 502s


if __name__ == "__main__":
    ThreadingHTTPServer(LISTEN, Relay).serve_forever()
