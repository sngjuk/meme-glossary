#!/usr/bin/env python3
"""Serve one hardened HTML page: a fixed meme image plus a 7-note FIFO board.

Stdlib only. Everything served comes from memory (the page, the image and the
vendored NES.css/font are read once at startup), so no request path ever
touches the filesystem. Run with --help for the knobs.
"""

import argparse
import hashlib
import http.server
import json
import os
import re
import secrets
import socket
import ssl
import sys
import tempfile
import threading
import time
import unicodedata
from collections import OrderedDict, deque

# --- limits -----------------------------------------------------------------

MAX_NOTES = 7                  # FIFO depth: the 8th note evicts the 1st
MAX_NOTE_CHARS = 280
MAX_NOTE_LINES = 8
MAX_BODY_BYTES = 4096          # request body hard cap
MAX_STORE_BYTES = 64 * 1024    # persisted board file hard cap
MAX_CONNECTIONS = 64           # concurrent sockets; extra ones are dropped
CONNECTION_TIMEOUT = 15.0      # seconds; bounds slow-loris style holds
REQUEST_QUEUE = 32

READ_LIMIT = (120, 60.0)       # per-IP requests per window
WRITE_LIMIT = (10, 60.0)       # per-IP note posts per window
GLOBAL_WRITE_LIMIT = (60, 60.0)
RATE_TABLE_MAX = 4096          # bounded so remote IPs cannot grow memory

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
WOFF2_MAGIC = b"wOF2"
LOG_SAFE = re.compile(r"[^\x20-\x7e]")
DIGITS = re.compile(r"[0-9]{1,10}")
# A Host header that is a bare IP literal cannot come from DNS rebinding
# (rebinding needs a name to re-point), so those are accepted on any bind.
IP_LITERAL = re.compile(r"^(?:\d{1,3}(?:\.\d{1,3}){3}|\[[0-9A-Fa-f:.]{2,45}\])$")


# --- note board -------------------------------------------------------------

def clean_note_text(raw):
    """Return sanitized note text, or None if it is not acceptable.

    Drops every Unicode control/format codepoint (this includes the bidi
    overrides used for text-spoofing) except newline and tab.
    """
    if not isinstance(raw, str):
        return None
    if len(raw) > MAX_NOTE_CHARS * 4:      # cheap bail-out before normalizing
        return None
    text = unicodedata.normalize("NFC", raw).replace("\r\n", "\n").replace("\r", "\n")
    text = "".join(
        ch for ch in text
        if ch in ("\n", "\t") or unicodedata.category(ch)[0] != "C"
    )
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if not text:
        return None
    if len(text) > MAX_NOTE_CHARS or text.count("\n") + 1 > MAX_NOTE_LINES:
        return None
    return text


class NoteBoard:
    """Thread-safe FIFO of at most MAX_NOTES notes, optionally persisted."""

    def __init__(self, store_path=None):
        self._lock = threading.Lock()
        self._notes = deque(maxlen=MAX_NOTES)
        self._store_path = store_path
        if store_path:
            self._load()

    def snapshot(self):
        with self._lock:
            return list(self._notes)

    def add(self, text):
        note = {"id": secrets.token_hex(8), "text": text, "ts": int(time.time())}
        with self._lock:
            self._notes.append(note)
            notes = list(self._notes)
            if self._store_path:
                self._save(notes)
        return notes

    # -- persistence (best effort; a broken file never takes the server down)

    def _load(self):
        try:
            if os.path.getsize(self._store_path) > MAX_STORE_BYTES:
                raise ValueError("store file too large")
            with open(self._store_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except FileNotFoundError:
            return
        except Exception as exc:                     # noqa: BLE001 - log and start empty
            log("store: ignoring unreadable file (%s)" % type(exc).__name__)
            return
        if not isinstance(data, list):
            log("store: ignoring file, expected a list")
            return
        for item in data[-MAX_NOTES:]:
            if not isinstance(item, dict):
                continue
            text = clean_note_text(item.get("text"))
            ts = item.get("ts")
            if text is None or not isinstance(ts, int):
                continue
            self._notes.append({"id": secrets.token_hex(8), "text": text, "ts": ts})
        log("store: loaded %d note(s)" % len(self._notes))

    def _save(self, notes):
        directory = os.path.dirname(self._store_path) or "."
        tmp_fd, tmp_path = tempfile.mkstemp(dir=directory, prefix=".notes-", suffix=".tmp")
        try:
            os.fchmod(tmp_fd, 0o600)
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as fh:
                json.dump(notes, fh, ensure_ascii=False)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp_path, self._store_path)
        except Exception as exc:                     # noqa: BLE001 - never fail a request
            log("store: write failed (%s)" % type(exc).__name__)
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


# --- rate limiting ----------------------------------------------------------

class RateLimiter:
    """Fixed-window counter with an LRU-bounded key table."""

    def __init__(self, limit, window):
        self._limit = limit
        self._window = window
        self._lock = threading.Lock()
        self._table = OrderedDict()

    def allow(self, key):
        """Return (allowed, retry_after_seconds)."""
        now = time.monotonic()
        with self._lock:
            entry = self._table.get(key)
            if entry is None or now - entry[0] >= self._window:
                entry = [now, 0]
            if entry[1] >= self._limit:
                self._table[key] = entry
                self._table.move_to_end(key)
                return False, max(1, int(self._window - (now - entry[0])) + 1)
            entry[1] += 1
            self._table[key] = entry
            self._table.move_to_end(key)
            while len(self._table) > RATE_TABLE_MAX:
                self._table.popitem(last=False)
            return True, 0


# --- http -------------------------------------------------------------------

def log(message):
    sys.stderr.write("[webnote] %s\n" % LOG_SAFE.sub("?", str(message))[:400])
    sys.stderr.flush()


class NoteHandler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    timeout = CONNECTION_TIMEOUT
    disable_nagle_algorithm = True                    # no 40ms stall on small replies
    server_version = "webnote"
    sys_version = ""                                  # do not leak the Python version

    # -- helpers

    def _base_headers(self, ctype, length, extra=None):
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(length))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Permissions-Policy",
                         "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
                         "magnetometer=(), microphone=(), payment=(), usb=()")
        if self.server.scheme == "https":
            # 180 days, this host only: no includeSubDomains, no preload.
            self.send_header("Strict-Transport-Security", "max-age=15552000")
        for key, value in (extra or {}).items():
            self.send_header(key, value)

    def _respond(self, status, body=b"", ctype="text/plain; charset=utf-8",
                 extra=None, head_only=False, close=False):
        if close:
            self.close_connection = True
        self.send_response(status)
        headers = dict(extra or {})
        if close:
            headers["Connection"] = "close"
        self._base_headers(ctype, len(body), headers)
        self.end_headers()
        if not head_only and body:
            self.wfile.write(body)

    def _json(self, status, payload, extra=None, close=False):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {"Cache-Control": "no-store"}
        headers.update(extra or {})
        self._respond(status, body, "application/json; charset=utf-8", headers, close=close)

    def _fail(self, status, code, extra=None):
        """Fixed error bodies: nothing from the request is ever echoed back."""
        self._json(status, {"error": code}, extra=extra, close=True)

    def version_string(self):
        return self.server_version                     # no trailing Python version

    def send_error(self, code, message=None, explain=None):
        """Replace the stdlib HTML error page (it echoes request data)."""
        if code in (405, 501):
            reason = "method_not_allowed"
        elif code < 500:
            reason = "bad_request"
        else:
            reason = "server_error"
        try:
            self._fail(code, reason)
        except Exception:                              # noqa: BLE001 - socket already gone
            self.close_connection = True

    def setup(self):
        """Finish the TLS handshake here, i.e. inside this connection's own thread.

        Wrapping the *listening* socket instead would run every handshake on the
        accept loop, where one slow client stalls every other connection.
        """
        if isinstance(self.request, ssl.SSLSocket):
            self.request.settimeout(CONNECTION_TIMEOUT)
            self.request.do_handshake()
        http.server.BaseHTTPRequestHandler.setup(self)

    def handle_one_request(self):
        self._t0 = time.perf_counter()
        self._nreq = getattr(self, "_nreq", 0) + 1
        http.server.BaseHTTPRequestHandler.handle_one_request(self)

    def log_request(self, code="-", size="-"):
        """Log how long the server itself took, and whether the socket was reused."""
        elapsed = (time.perf_counter() - getattr(self, "_t0", time.perf_counter())) * 1000
        log("%s %s -> %s  %.2fms  (request #%d on this connection)"
            % (self.client_address[0], self.requestline, code, elapsed,
               getattr(self, "_nreq", 1)))

    def log_message(self, fmt, *args):
        log("%s %s" % (self.client_address[0], fmt % args))

    def log_error(self, fmt, *args):
        log("%s error: %s" % (self.client_address[0], fmt % args))

    # -- request gates

    def _host_ok(self):
        """Reject anything but the hostnames we were told to answer for.

        This is the DNS-rebinding guard: an attacker page resolving its own
        domain to 127.0.0.1 still arrives with a foreign Host header.
        """
        hosts = self.headers.get_all("Host") or []
        if len(hosts) != 1:                            # duplicate Host: smuggling bait
            return False
        host = hosts[0].strip().lower()
        if host in self.server.allowed_hosts:
            return True
        if ":" in host and not host.endswith("]"):
            name, _, port = host.rpartition(":")
        else:
            name, port = host, ""
        if port != str(self.server.server_address[1]):
            return False
        return bool(IP_LITERAL.match(name))

    def _same_origin_fetch(self):
        """True unless the browser tells us this request came from elsewhere."""
        site = (self.headers.get("Sec-Fetch-Site") or "").strip().lower()
        return site in ("", "same-origin", "none")

    def _read_body(self):
        """Return (bytes, error_code). Chunked bodies are refused outright."""
        if self.headers.get_all("Transfer-Encoding"):
            return None, "unsupported_encoding"
        lengths = self.headers.get_all("Content-Length") or []
        if not lengths:
            return None, "length_required"
        if len(lengths) != 1:                          # conflicting lengths: smuggling bait
            return None, "bad_length"
        raw_len = lengths[0].strip()
        # Strict digits only: int() would also accept "+5", "5_0" and non-ASCII digits.
        if not DIGITS.fullmatch(raw_len):
            return None, "bad_length"
        length = int(raw_len)
        if length > MAX_BODY_BYTES:
            return None, "too_large"
        body = self.rfile.read(length)
        if len(body) != length:
            return None, "truncated_body"
        return body, None

    def _rate(self, limiter, key):
        allowed, retry = limiter.allow(key)
        if not allowed:
            self._fail(429, "rate_limited", extra={"Retry-After": str(retry)})
        return allowed

    # -- routes

    def do_GET(self):
        self._handle(head_only=False)

    def do_HEAD(self):
        self._handle(head_only=True)

    def do_POST(self):
        srv = self.server
        if not self._host_ok():
            return self._fail(421, "bad_host")
        if not self._rate(srv.read_limiter, self.client_address[0]):
            return
        path = self.path.split("?", 1)[0].split("#", 1)[0]
        if path != "/api/notes":
            self._read_body()                          # drain so the socket stays sane
            if path == "/" or path in srv.static:
                return self._fail(405, "method_not_allowed")
            return self._fail(404, "not_found")
        return self._post_note()

    def _handle(self, head_only):
        srv = self.server
        if not self._host_ok():
            return self._fail(421, "bad_host")
        if not self._rate(srv.read_limiter, self.client_address[0]):
            return
        path = self.path.split("?", 1)[0].split("#", 1)[0]

        if path == "/":
            nonce = secrets.token_urlsafe(18)
            body = srv.page_template.replace("{{CSP_NONCE}}", nonce).encode("utf-8")
            csp = ("default-src 'none'; img-src 'self' data:; "
                   "style-src 'self' 'nonce-%s'; script-src 'nonce-%s'; "
                   "font-src 'self'; connect-src 'self'; base-uri 'none'; "
                   "form-action 'none'; frame-ancestors 'none'" % (nonce, nonce))
            return self._respond(200, body, "text/html; charset=utf-8",
                                 {"Content-Security-Policy": csp, "Cache-Control": "no-store"},
                                 head_only=head_only)

        asset = srv.static.get(path)
        if asset is not None:
            ctype, data, etag = asset
            headers = {"ETag": etag, "Cache-Control": "public, max-age=3600"}
            if self.headers.get("If-None-Match") == etag:
                return self._respond(304, b"", ctype, headers, head_only=True)
            return self._respond(200, data, ctype, headers, head_only=head_only)

        if path == "/api/notes":
            if not self._same_origin_fetch():
                return self._fail(403, "cross_origin")
            payload = {"max": MAX_NOTES, "maxChars": MAX_NOTE_CHARS,
                       "notes": srv.board.snapshot()}
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            return self._respond(200, body, "application/json; charset=utf-8",
                                 {"Cache-Control": "no-store"}, head_only=head_only)

        return self._fail(404, "not_found")

    def _post_note(self):
        srv = self.server

        # CSRF: three independent checks, each sufficient on a modern browser.
        if not self._same_origin_fetch():
            return self._fail(403, "cross_origin")
        origin = (self.headers.get("Origin") or "").strip().lower()
        host = (self.headers.get("Host") or "").strip().lower()
        # The Host header already passed _host_ok(), so "http://<host>" is this
        # page's own origin; a cross-site post carries the attacker's origin instead.
        if origin not in srv.allowed_origins and origin != srv.scheme + "://" + host:
            return self._fail(403, "bad_origin")
        ctype = (self.headers.get("Content-Type") or "").split(";", 1)[0].strip().lower()
        if ctype != "application/json":
            return self._fail(415, "bad_content_type")

        body, err = self._read_body()
        if err:
            status = {"too_large": 413, "length_required": 411}.get(err, 400)
            return self._fail(status, err)

        if not self._rate(srv.global_write_limiter, "*"):
            return
        if not self._rate(srv.write_limiter, self.client_address[0]):
            return

        try:
            # RecursionError: json's parser recurses, so deeply nested input would
            # otherwise escape as an unhandled error and drop the connection.
            data = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, ValueError, RecursionError):
            return self._fail(400, "bad_json")
        if not isinstance(data, dict):
            return self._fail(400, "bad_json")

        text = clean_note_text(data.get("text"))
        if text is None:
            return self._fail(422, "bad_note")

        notes = srv.board.add(text)
        log("note added (%d chars), board holds %d" % (len(text), len(notes)))
        return self._json(201, {"max": MAX_NOTES, "maxChars": MAX_NOTE_CHARS, "notes": notes})


class NoteServer(http.server.ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True
    request_queue_size = REQUEST_QUEUE

    def __init__(self, address, handler, page_template, static, board,
                 allowed_hosts, allowed_origins, ssl_context=None):
        if ":" in address[0]:
            self.address_family = socket.AF_INET6
        self.ssl_context = ssl_context
        self.scheme = "https" if ssl_context else "http"
        super().__init__(address, handler)
        self.page_template = page_template
        self.static = static
        self.board = board
        self.allowed_hosts = allowed_hosts
        self.allowed_origins = allowed_origins
        self.read_limiter = RateLimiter(*READ_LIMIT)
        self.write_limiter = RateLimiter(*WRITE_LIMIT)
        self.global_write_limiter = RateLimiter(*GLOBAL_WRITE_LIMIT)
        self._slots = threading.BoundedSemaphore(MAX_CONNECTIONS)

    def get_request(self):
        """Accept plainly and wrap; the handshake itself happens in setup()."""
        sock, addr = super().get_request()
        if self.ssl_context is not None:
            sock = self.ssl_context.wrap_socket(sock, server_side=True,
                                                do_handshake_on_connect=False)
        return sock, addr

    def process_request(self, request, client_address):
        if not self._slots.acquire(blocking=False):
            log("connection refused: %d in flight" % MAX_CONNECTIONS)
            self.close_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self._slots.release()
            raise

    def shutdown_request(self, request):
        try:
            super().shutdown_request(request)
        finally:
            self._slots.release()

    def handle_error(self, request, client_address):
        exc = sys.exc_info()[1]
        log("handler error from %s: %s" % (client_address[0], type(exc).__name__))


class RedirectHandler(http.server.BaseHTTPRequestHandler):
    """Answers plain HTTP with a redirect to this board's HTTPS origin.

    It never reflects the request path and only trusts a Host it recognises, so
    it cannot be turned into an open redirect.
    """

    protocol_version = "HTTP/1.1"
    timeout = CONNECTION_TIMEOUT
    server_version = "webnote"
    sys_version = ""

    def version_string(self):
        return self.server_version

    def _send(self, status, headers):
        self.close_connection = True
        self.send_response(status)
        for key, value in headers.items():
            self.send_header(key, value)
        self.send_header("Content-Length", "0")
        self.send_header("Connection", "close")
        self.end_headers()

    def do_GET(self):
        hosts = self.headers.get_all("Host") or []
        host = hosts[0].strip().lower() if len(hosts) == 1 else ""
        name = host.rpartition(":")[0] if (":" in host and not host.endswith("]")) else host
        target = self.server.targets.get(name)
        if target is None:
            return self._send(421, {})
        self._send(308, {"Location": target, "Cache-Control": "no-store"})

    do_HEAD = do_GET
    do_POST = do_GET

    def log_message(self, fmt, *args):
        log("%s redirect %s" % (self.client_address[0], fmt % args))

    def log_error(self, fmt, *args):
        log("%s redirect error: %s" % (self.client_address[0], fmt % args))


class RedirectServer(http.server.ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address, targets):
        if ":" in address[0]:
            self.address_family = socket.AF_INET6
        super().__init__(address, RedirectHandler)
        self.targets = targets

    def handle_error(self, request, client_address):
        log("redirect handler error from %s: %s"
            % (client_address[0], type(sys.exc_info()[1]).__name__))


def build_tls_context(cert_path, key_path):
    """A TLS 1.2+ server context; the stdlib default cipher list is already sane."""
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.options |= ssl.OP_NO_COMPRESSION | ssl.OP_CIPHER_SERVER_PREFERENCE
    try:
        context.load_cert_chain(cert_path, key_path)
    except (OSError, ssl.SSLError) as exc:
        raise SystemExit("cannot load the certificate/key: %s" % exc)
    return context


# --- startup ----------------------------------------------------------------

def _read(path):
    try:
        with open(path, "rb") as fh:
            return fh.read()
    except OSError as exc:
        raise SystemExit("cannot read %s (%s)" % (path, exc.strerror))


def load_assets(here, image_path):
    """Read every byte the server will ever serve, and sanity-check it.

    Returns (page_template, static_table). The table maps a URL path to
    (content_type, bytes, etag); nothing is read from disk after this point.
    """
    page = _read(os.path.join(here, "index.html")).decode("utf-8")
    if "{{CSP_NONCE}}" not in page:
        raise SystemExit("index.html is missing the {{CSP_NONCE}} placeholder")

    image = _read(image_path)
    if not image.startswith(PNG_MAGIC):
        raise SystemExit("%s is not a PNG file" % image_path)

    css_path = os.path.join(here, "assets", "nes-core.min.css")
    css = _read(css_path)
    try:
        css.decode("utf-8")
    except UnicodeDecodeError:
        raise SystemExit("%s is not valid UTF-8" % css_path)

    font_path = os.path.join(here, "assets", "press-start-2p.woff2")
    font = _read(font_path)
    if not font.startswith(WOFF2_MAGIC):
        raise SystemExit("%s is not a woff2 file" % font_path)

    table = {}
    for path, ctype, data in (
        ("/image", "image/png", image),
        ("/assets/nes-core.min.css", "text/css; charset=utf-8", css),
        ("/assets/press-start-2p.woff2", "font/woff2", font),
    ):
        table[path] = (ctype, data, '"%s"' % hashlib.sha256(data).hexdigest()[:32])
    return page, table


def build_allowlists(host, port, extra_hosts, extra_origins, scheme="http"):
    names = {"localhost", "127.0.0.1", "[::1]"}
    if host not in ("0.0.0.0", "::", ""):
        names.add("[%s]" % host if ":" in host else host)
    names.update(h.strip().lower() for h in extra_hosts if h.strip())
    hosts = set()
    for name in names:
        hosts.add("%s:%d" % (name, port))
        if port in (80, 443):
            hosts.add(name)
    origins = {"%s://%s" % (scheme, h) for h in hosts}
    origins.update(o.strip().lower().rstrip("/") for o in extra_origins if o.strip())
    return hosts, origins


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    parser = argparse.ArgumentParser(description="Serve the meme note board.")
    parser.add_argument("--host", default="0.0.0.0",
                        help="bind address (default: 0.0.0.0, reachable from the network; "
                             "use 127.0.0.1 for loopback only)")
    parser.add_argument("--port", type=int, default=8000, help="bind port (default: 8000)")
    parser.add_argument("--image", default=os.path.join(here, "metro_image.png"),
                        help="PNG shown at the top of the page")
    parser.add_argument("--store", default=None,
                        help="optional JSON file to persist notes across restarts")
    parser.add_argument("--allowed-host", action="append", default=[],
                        help="extra Host header value to accept (repeatable)")
    parser.add_argument("--tls-cert", default=None,
                        help="PEM certificate chain; serves HTTPS when given with --tls-key")
    parser.add_argument("--tls-key", default=None, help="PEM private key for --tls-cert")
    parser.add_argument("--redirect-http", type=int, default=None,
                        help="also listen on this plain-HTTP port and 308 every request "
                             "to the HTTPS board (e.g. 80)")
    parser.add_argument("--allowed-origin", action="append", default=[],
                        help="extra Origin to accept for posts, e.g. https://notes.example "
                             "(repeatable; needed behind a TLS proxy)")
    args = parser.parse_args()

    if not 1 <= args.port <= 65535:
        raise SystemExit("--port must be in 1..65535")
    if bool(args.tls_cert) != bool(args.tls_key):
        raise SystemExit("--tls-cert and --tls-key must be given together")
    if args.redirect_http is not None:
        if not args.tls_cert:
            raise SystemExit("--redirect-http only makes sense with TLS enabled")
        if not 1 <= args.redirect_http <= 65535 or args.redirect_http == args.port:
            raise SystemExit("--redirect-http must be a free port in 1..65535")

    tls = build_tls_context(args.tls_cert, args.tls_key) if args.tls_cert else None
    scheme = "https" if tls else "http"

    page, static = load_assets(here, args.image)
    hosts, origins = build_allowlists(args.host, args.port, args.allowed_host,
                                      args.allowed_origin, scheme)
    board = NoteBoard(args.store)
    server = NoteServer((args.host, args.port), NoteHandler, page, static, board,
                        hosts, origins, tls)

    redirector = None
    if args.redirect_http is not None:
        suffix = "" if args.port == 443 else ":%d" % args.port
        targets = {}
        for allowed in hosts:
            name = allowed.rpartition(":")[0] if (":" in allowed and
                                                  not allowed.endswith("]")) else allowed
            targets[name] = "https://%s%s/" % (name, suffix)
        redirector = RedirectServer((args.host, args.redirect_http), targets)
        threading.Thread(target=redirector.serve_forever, daemon=True).start()
        log("redirecting http://<host>:%d/ -> https://<host>%s/"
            % (args.redirect_http, suffix))

    if args.host not in ("127.0.0.1", "::1", "localhost"):
        log("WARNING: bound to %s - anyone who can reach this port can post a note; "
            "there is no authentication." % args.host)
    if not tls:
        log("WARNING: no TLS - traffic is plaintext and can be read or rewritten in "
            "transit. Pass --tls-cert/--tls-key for HTTPS.")
    log("serving %s://%s:%d/ (notes: %d max, FIFO)"
        % (scheme, args.host, args.port, MAX_NOTES))
    log("accepting Host: %s, or any IP literal on port %d "
        "(a domain name needs --allowed-host)" % (", ".join(sorted(hosts)), args.port))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log("shutting down")
    finally:
        server.server_close()
        if redirector is not None:
            redirector.shutdown()
            redirector.server_close()


if __name__ == "__main__":
    main()
