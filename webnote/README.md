# webnote

One hardened page in 8-bit style: a fixed meme image on top, a free-form note board
underneath that holds **at most 7 notes, FIFO** — the 8th note pushes the 1st off the
board.

Stdlib Python only, no runtime dependencies and no CDN calls: the CSS and the font are
vendored into `assets/` and served from this process.

## Run

```
python3 webnote/server.py                        # http://<this machine>:8000/
python3 webnote/server.py --host 127.0.0.1       # loopback only
python3 webnote/server.py --store notes.json     # survive restarts

# HTTPS, terminated by this process - no nginx, no second daemon:
sudo python3 webnote/server.py --port 443 --redirect-http 80 \
     --tls-cert /etc/letsencrypt/live/<domain>/fullchain.pem \
     --tls-key  /etc/letsencrypt/live/<domain>/privkey.pem \
     --allowed-host <domain>
```

There is nothing to install — see `requirements.txt`; the standard library is the
whole dependency list.

On a server, use the launcher instead of typing flags. It reads `webnote.env` next to
it (copy `webnote.env.example`), refuses to source that file if it is group- or
world-writable, validates the settings before starting, and warns when TLS is off or
a key is readable beyond its owner:

```
./run.sh              # foreground - this is the form to use under systemd/launchd
./run.sh start        # background, pid in webnote.pid, output in webnote.log
./run.sh status | stop | restart | logs
```

`start` fully detaches: `nohup` (so the SIGHUP an SSH logout sends is ignored), stdin
from `/dev/null` (otherwise `ssh` hangs waiting for the pty to close) and `disown`.
Reconnect and `./run.sh status` finds it again by its pidfile.

**That is still not enough on every host.** Distros that ship
`logind.conf` with `KillUserProcesses=yes` (Fedora, RHEL, Arch, openSUSE — Debian and
Ubuntu patch it back to `no`) kill *every* process in the login session's cgroup at
logout, and `nohup` cannot help: the kill targets the cgroup, not the process group.
Check with

```
grep -r KillUserProcesses /etc/systemd/logind.conf /etc/systemd/logind.conf.d/ 2>/dev/null
loginctl show-user "$USER" | grep -i linger
```

If it is `yes`, either `sudo loginctl enable-linger "$USER"` (keeps the user manager,
and its processes, alive after logout) or — better — install the unit below. Neither
`./run.sh start` nor a unit-less tmux survives a reboot; the unit does.

A systemd unit is shipped as `webnote.service` (copy it to
`/etc/systemd/system/`, fix `User=` and the paths, `systemctl enable --now webnote`):

```ini
[Unit]
Description=webnote board
After=network-online.target

[Service]
Type=exec
User=webnote
WorkingDirectory=/opt/meme-glossary/webnote
ExecStart=/opt/meme-glossary/webnote/run.sh
Restart=on-failure
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/var/lib/webnote
# only when binding 80/443 as a non-root user:
AmbientCapabilities=CAP_NET_BIND_SERVICE

[Install]
WantedBy=multi-user.target
```

Certbot renewal replaces the certificate files, and the server reads them once at
startup — hook a restart onto renewal (`--deploy-hook "systemctl restart webnote"`).

| flag | default | meaning |
| --- | --- | --- |
| `--host` | `0.0.0.0` | bind address; reachable from the network. `127.0.0.1` for loopback only |
| `--port` | `8000` | bind port |
| `--image` | `webnote/metro_image.png` | the PNG shown at the top |
| `--store` | *(none)* | JSON file the board is written to; without it notes live in memory |
| `--allowed-host` | – | extra `Host:` value to accept (repeatable) |
| `--allowed-origin` | – | extra `Origin:` to accept for posts, e.g. `https://notes.example` (repeatable) |
| `--tls-cert` / `--tls-key` | – | PEM chain + key; given together the board serves HTTPS itself |
| `--redirect-http` | – | extra plain-HTTP port that 308s to the HTTPS board (e.g. `80`) |

Routes: `GET /` (page), `GET /image`, `GET /assets/nes-core.min.css`,
`GET /assets/press-start-2p.woff2`, `GET|POST /api/notes`. Everything else is 404, and
no other method is served.

Every request is logged with the time the server itself spent on it and whether the
socket was reused, e.g. `POST /api/notes -> 201  0.20ms  (request #6 on this
connection)` — enough to tell a slow server apart from a slow page.

`--store` costs one `fsync` per accepted note; without it a post is ~0.2 ms server-side.
The page renders a new note optimistically and reconciles with the server's list when
the reply lands, so typing never waits on the round trip.

## TLS

`--tls-cert` / `--tls-key` make this process the TLS endpoint: TLS 1.2 minimum
(1.3 when the client offers it), compression off, server cipher preference, and
`Strict-Transport-Security: max-age=15552000` on every response. Handshakes run in the
connection's own thread — the listening socket is *not* wrapped — so one slow client
cannot stall the accept loop. With TLS on, the post-time `Origin` check switches to
`https://`, so an `http://` origin is rejected. `--redirect-http 80` adds a second
listener that answers every plain request with a 308 to the HTTPS board; it never
reflects the request path and only answers for a recognised `Host`, so it cannot be
used as an open redirect.

Getting a certificate, in order of preference:

1. **A domain + certbot.** `sudo certbot certonly --standalone -d <domain>` writes
   `fullchain.pem`/`privkey.pem` under `/etc/letsencrypt/live/<domain>/`; point
   `--tls-cert`/`--tls-key` at them and pass `--allowed-host <domain>`. Renewal is
   `certbot renew` plus a restart of this server (the certificate is read once at
   startup). Certbot needs port 80 free at renewal time, so stop `--redirect-http`
   for that minute, or renew with the DNS challenge.
2. **A tunnel** (`cloudflared tunnel --url http://127.0.0.1:8000`, Tailscale Funnel).
   No certificate, no open port; bind the board to `127.0.0.1` and pass
   `--allowed-host`/`--allowed-origin` for the tunnel hostname. The tunnel provider
   terminates TLS, so it sees the plaintext.
3. **Self-signed** — fine on a LAN, *not* real protection on the public internet: the
   browser warns, and a user trained to click through would click through an
   attacker's certificate just the same.

   ```
   openssl req -x509 -newkey rsa:2048 -nodes -days 90 \
     -keyout key.pem -out cert.pem -subj "/CN=$(hostname)" \
     -addext "subjectAltName=IP:<your ip>"
   ```

## Vendored assets

| file | source | licence | sha256 |
| --- | --- | --- | --- |
| `assets/nes-core.min.css` | NES.css 2.3.0, `css/nes-core.min.css` | MIT (`assets/nes.css-LICENSE`) | `4e296c17…3626b5` |
| `assets/press-start-2p.woff2` | Google Fonts, Press Start 2P v16 (latin subset) | SIL OFL 1.1 (`assets/press-start-2p-OFL.txt`) | `42144b97…99ae6e` |

Both were downloaded once and checked before being committed: the CSS was fetched from
cdnjs *and* jsdelivr and the two copies hash identically, it contains no `@import` and
no external `url()` (only inline `data:` sprites), and the font begins with the `wOF2`
magic. The server re-validates all of this at startup (UTF-8 CSS, `wOF2` font, PNG
image) and refuses to start otherwise. Nothing is fetched at request time, so a CDN
compromise cannot reach a running instance.

## Security model

The threat model is a public-ish page with no accounts: anyone who can reach the port
can write a note. What is defended is everything *around* that — the browser, the
process, and the box.

**No filesystem in the request path.** `index.html`, the image, the CSS and the font
are read once at startup and served from memory. There is no static-file handler, so
path traversal, symlink tricks and `%2e%2e` encodings have nothing to reach; every
unknown path is a flat 404.

**XSS.** CSP is `default-src 'none'` with a fresh per-response nonce for the one inline
`<style>` and `<script>`; `style-src`/`font-src` additionally allow `'self'` for the
vendored stylesheet and font, and `img-src` allows `data:` because NES.css draws its
sprites as inline SVG. Script stays nonce-only — no `'unsafe-inline'`, no external
origin. Note text is inserted into the DOM as a text node — the page contains no
`innerHTML`, no inline handlers and no inline style attributes — so a stored `<script>`
payload can only ever render as characters. `base-uri` and `form-action` are `'none'`,
`frame-ancestors 'none'` (plus `X-Frame-Options: DENY`), and responses carry `nosniff`,
`no-referrer`, COOP and CORP.

**CSRF.** A note post must satisfy three independent checks: `Sec-Fetch-Site` is not
cross-site, `Origin` is on the allowlist, and `Content-Type` is `application/json`
(which is not a CORS-simple type, so a cross-origin attempt needs a preflight that is
never answered). No CORS headers are ever emitted and no cookies are used.

**DNS rebinding.** The `Host` header must be an IP literal on the bound port, or a
name the server was started for (`localhost`, `127.0.0.1`, `[::1]` plus
`--allowed-host`); anything else is 421, and a duplicate `Host` header is rejected
outright. IP literals are safe to accept because rebinding needs a *name* to
re-point at the target — reaching this server through a domain still requires
`--allowed-host`. The post-time `Origin` check is derived from that verified `Host`,
so it keeps working on whatever address the board is reached at.

**Request smuggling / desync.** Chunked bodies are refused, `Content-Length` must be a
single strictly-numeric header (so `+5`, `1_3` and non-ASCII digits are rejected), and
every error response closes the connection instead of leaving a half-read body on a
keep-alive socket.

**Resource exhaustion.** 4 KB body cap (checked before a single byte is read), 64
concurrent connections (extras are closed immediately), 15 s socket timeout so a
slow-loris hold cannot park a thread, and the stdlib caps on request-line (414) and
header count (431). Rate limits are 120 requests/min per IP, 10 notes/min per IP and
60 notes/min overall, with `Retry-After`; the limiter table is LRU-bounded at 4096 keys
so remote IPs cannot grow it without limit.

**Input validation.** A note is NFC-normalized, stripped of every Unicode control and
format codepoint except newline/tab (this removes the bidi overrides used for display
spoofing), collapsed to at most one blank line, and must end up non-empty, ≤ 280
characters and ≤ 8 lines. Anything else is 422.

**Output hygiene.** Error bodies are fixed strings — no request data is ever echoed
back, which also replaces the stdlib's HTML error page. The `Server` header carries no
version. Logs are stripped of non-printable characters and truncated, and note bodies
are never logged (only their length).

**Persistence.** With `--store`, the board is written atomically (temp file in the same
directory, `chmod 0600`, `os.replace`) and re-validated through the same sanitizer on
load; a corrupt or oversized file is ignored rather than fatal.

### What is deliberately *not* covered

- **No authentication and no per-author identity.** The default bind is `0.0.0.0`, so
  anyone who can reach port 8000 — everyone on the LAN, and the whole internet if the
  port is forwarded — can post. The rate limiter (10 notes/min per IP, 60/min overall)
  is the only brake, and the startup log warns about it every time.
- **TLS is opt-in.** Without `--tls-cert`/`--tls-key` the traffic is plaintext and can
  be read *and rewritten* in transit; the server warns at startup. Behind a tunnel or
  proxy, the per-IP rate limiter sees the proxy's address — it does not trust
  `X-Forwarded-For`, which would be spoofable.
- **Availability.** The 64-connection cap keeps the process alive but not reachable:
  one host holding 64 sockets open occupies every slot until the 15 s timeout.
- Binding to anything other than loopback prints a warning at startup, on purpose.
