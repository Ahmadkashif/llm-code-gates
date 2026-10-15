"""HTTP API (stdlib): GET /up, POST /v1/quote, GET /v1/quote/<id>."""
from __future__ import annotations

import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .pricing import PricingError, quote
from .ratelimit import TokenBucket
from .store import QuoteStore
from .validation import ValidationError, parse_request

MAX_BODY = 4096
QUOTE_PATH = re.compile(r"^/v1/quote/([0-9a-f]{32})$")


def make_handler(store: QuoteStore, limiter: TokenBucket):
    class Handler(BaseHTTPRequestHandler):
        server_version = "parcel-quote/0.1"

        def log_message(self, fmt, *args):  # keep test output quiet
            pass

        def _send(self, code: int, payload: dict) -> None:
            body = json.dumps(payload).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/up":
                return self._send(200, {"status": "ok"})
            m = QUOTE_PATH.match(self.path)
            if m:
                q = store.get(m.group(1))
                return self._send(200, q) if q else self._send(404, {"error": "not found"})
            self._send(404, {"error": "not found"})

        def do_POST(self):
            if self.path != "/v1/quote":
                return self._send(404, {"error": "not found"})
            if not limiter.allow(self.client_address[0]):
                return self._send(429, {"error": "rate limited"})
            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0 or length > MAX_BODY:
                return self._send(413 if length > MAX_BODY else 400, {"error": "bad body size"})
            try:
                req = parse_request(json.loads(self.rfile.read(length)))
                q = quote(req["weight_kg"], req["zone"], req["quantity"], req["promo"])
            except json.JSONDecodeError:
                return self._send(400, {"error": "invalid JSON"})
            except ValidationError as e:
                return self._send(422, {"error": str(e), "field": e.field})
            except PricingError as e:
                return self._send(422, {"error": str(e)})
            qid = store.save(req["zone"], req["quantity"], q.total)
            self._send(201, {"id": qid, "unit_price": str(q.unit_price), "subtotal": str(q.subtotal),
                             "discount": str(q.discount), "total": str(q.total)})
    return Handler


def build_server(host: str = "127.0.0.1", port: int = 0, store: QuoteStore | None = None,
                 limiter: TokenBucket | None = None) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), make_handler(store or QuoteStore(),
                                                          limiter or TokenBucket(rate_per_s=5, burst=20)))


def main() -> None:  # pragma: no cover
    srv = build_server(os.environ.get("HOST", "127.0.0.1"), int(os.environ.get("PORT", "8080")))
    srv.serve_forever()


if __name__ == "__main__":  # pragma: no cover
    main()
