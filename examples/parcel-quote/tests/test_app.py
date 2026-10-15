"""Integration tests: real HTTP server on an ephemeral port."""
import json
import threading
import urllib.error
import urllib.request

import pytest

from quotesvc.app import build_server
from quotesvc.ratelimit import TokenBucket

pytestmark = pytest.mark.integration


@pytest.fixture()
def base_url():
    srv = build_server(limiter=TokenBucket(rate_per_s=1000, burst=1000))
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


def call(url, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"},
                                 method="POST" if data else "GET")
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def test_up(base_url):
    assert call(base_url + "/up") == (200, {"status": "ok"})


def test_quote_roundtrip(base_url):
    code, body = call(base_url + "/v1/quote", {"weight_kg": 1, "zone": "eu", "quantity": 2})
    assert code == 201
    assert body["total"] == "17.60"
    code, stored = call(base_url + f"/v1/quote/{body['id']}")
    assert code == 200
    assert stored["total"] == "17.60"


def test_validation_error(base_url):
    code, body = call(base_url + "/v1/quote", {"weight_kg": -1, "zone": "eu"})
    assert code == 422
    assert body["field"] == "weight_kg"


def test_rate_limit():
    srv = build_server(limiter=TokenBucket(rate_per_s=0.001, burst=1))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_address[1]}/v1/quote"
    try:
        assert call(url, {"weight_kg": 1, "zone": "eu"})[0] == 201
        assert call(url, {"weight_kg": 1, "zone": "eu"})[0] == 429
    finally:
        srv.shutdown()
