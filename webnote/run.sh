#!/usr/bin/env bash
#
# Launcher for the webnote board.
#
#   ./run.sh                 run in the foreground (use this under systemd/launchd)
#   ./run.sh start|stop|restart|status|logs
#
# Configure with environment variables, or with a webnote.env file next to this
# script holding the same names (KEY=value, one per line).
#
#   HOST=0.0.0.0 PORT=8000 STORE=notes.json ./run.sh start
#
set -euo pipefail

DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
ENV_FILE="${WEBNOTE_ENV:-$DIR/webnote.env}"

CMD="${1:-run}"

die() { printf 'run.sh: %s\n' "$1" >&2; exit 1; }
warn() { printf 'run.sh: %s\n' "$1" >&2; }
# How the server *would* start is noise for status/stop/logs.
notice() { case "$CMD" in run|start|restart) warn "$1" ;; esac; }

# Mode bits, portably (BSD stat vs GNU stat).
mode_of() { stat -f '%Lp' "$1" 2>/dev/null || stat -c '%a' "$1" 2>/dev/null || echo ""; }

if [ -f "$ENV_FILE" ]; then
  m="$(mode_of "$ENV_FILE")"
  case "$m" in
    *[2367]) die "$ENV_FILE is group/world-writable (mode $m); this script sources it" ;;
  esac
  # shellcheck disable=SC1090
  . "$ENV_FILE"
fi

PYTHON="${PYTHON:-python3}"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
STORE="${STORE:-}"
IMAGE="${IMAGE:-}"
TLS_CERT="${TLS_CERT:-}"
TLS_KEY="${TLS_KEY:-}"
REDIRECT_HTTP="${REDIRECT_HTTP:-}"
ALLOWED_HOSTS="${ALLOWED_HOSTS:-}"      # space separated
ALLOWED_ORIGINS="${ALLOWED_ORIGINS:-}"  # space separated
LOG="${LOG:-$DIR/webnote.log}"
PIDFILE="${PIDFILE:-$DIR/webnote.pid}"

command -v "$PYTHON" >/dev/null 2>&1 || die "$PYTHON not found"
[ -f "$DIR/server.py" ] || die "server.py is missing next to this script"
case "$PORT" in ''|*[!0-9]*) die "PORT must be a number (got '$PORT')" ;; esac
[ "$PORT" -ge 1 ] && [ "$PORT" -le 65535 ] || die "PORT must be in 1..65535"

# --- build the argument list -------------------------------------------------
args=("$DIR/server.py" --host "$HOST" --port "$PORT")
[ -n "$STORE" ] && args+=(--store "$STORE")
[ -n "$IMAGE" ] && args+=(--image "$IMAGE")

if [ -n "$TLS_CERT" ] || [ -n "$TLS_KEY" ]; then
  [ -n "$TLS_CERT" ] && [ -n "$TLS_KEY" ] || die "set both TLS_CERT and TLS_KEY, or neither"
  [ -r "$TLS_CERT" ] || die "cannot read TLS_CERT: $TLS_CERT"
  [ -r "$TLS_KEY" ]  || die "cannot read TLS_KEY: $TLS_KEY"
  km="$(mode_of "$TLS_KEY")"
  case "$km" in
    *[1-7][0-7]|*[0-7][1-7]) notice "TLS_KEY $TLS_KEY is readable beyond its owner (mode $km)" ;;
  esac
  args+=(--tls-cert "$TLS_CERT" --tls-key "$TLS_KEY")
  if [ -n "$REDIRECT_HTTP" ]; then
    case "$REDIRECT_HTTP" in ''|*[!0-9]*) die "REDIRECT_HTTP must be a number" ;; esac
    args+=(--redirect-http "$REDIRECT_HTTP")
  fi
elif [ -n "$REDIRECT_HTTP" ]; then
  die "REDIRECT_HTTP needs TLS_CERT/TLS_KEY"
else
  notice "no TLS configured - traffic will be plaintext"
fi

for h in $ALLOWED_HOSTS; do args+=(--allowed-host "$h"); done
for o in $ALLOWED_ORIGINS; do args+=(--allowed-origin "$o"); done

if [ "$PORT" -lt 1024 ] && [ "$(id -u)" -ne 0 ]; then
  notice "port $PORT needs root on most systems; start this with sudo if the bind fails"
fi
if [ "$(id -u)" -eq 0 ] && [ "$PORT" -ge 1024 ] && [ -z "$TLS_CERT" ]; then
  notice "running as root is not needed for port $PORT"
fi

# --- process control ---------------------------------------------------------
running_pid() {
  [ -f "$PIDFILE" ] || return 1
  local pid
  pid="$(cat "$PIDFILE" 2>/dev/null || true)"
  case "$pid" in ''|*[!0-9]*) return 1 ;; esac
  kill -0 "$pid" 2>/dev/null || return 1
  printf '%s' "$pid"
}

start() {
  if pid="$(running_pid)"; then die "already running (pid $pid)"; fi
  umask 077
  : > "$LOG" || die "cannot write the log file: $LOG"
  # Detach from the terminal completely so an SSH logout cannot take it down:
  # nohup ignores SIGHUP, </dev/null frees the pty (otherwise ssh hangs on exit),
  # and disown drops it from this shell's job table.
  nohup "$PYTHON" "${args[@]}" </dev/null >>"$LOG" 2>&1 &
  local pid=$!
  disown "$pid" 2>/dev/null || true
  printf '%s\n' "$pid" > "$PIDFILE"
  sleep 1
  if ! kill -0 "$pid" 2>/dev/null; then
    rm -f "$PIDFILE"
    warn "the server exited immediately; last lines of $LOG:"
    tail -n 15 "$LOG" >&2 || true
    exit 1
  fi
  printf 'started (pid %s), logging to %s\n' "$pid" "$LOG"
  tail -n 4 "$LOG" || true
}

stop() {
  local pid
  if ! pid="$(running_pid)"; then rm -f "$PIDFILE"; printf 'not running\n'; return 0; fi
  kill -TERM "$pid" 2>/dev/null || true
  for _ in $(seq 1 50); do
    kill -0 "$pid" 2>/dev/null || break
    sleep 0.1
  done
  if kill -0 "$pid" 2>/dev/null; then
    warn "did not stop on SIGTERM, sending SIGKILL"
    kill -KILL "$pid" 2>/dev/null || true
  fi
  rm -f "$PIDFILE"
  printf 'stopped (pid %s)\n' "$pid"
}

case "$CMD" in
  run)     umask 077; exec "$PYTHON" "${args[@]}" ;;
  start)   start ;;
  stop)    stop ;;
  restart) stop; start ;;
  status)
    if pid="$(running_pid)"; then
      printf 'running (pid %s) on %s://%s:%s/\n' \
        "$pid" "$([ -n "$TLS_CERT" ] && echo https || echo http)" "$HOST" "$PORT"
    else
      printf 'not running\n'; exit 1
    fi ;;
  logs)    exec tail -n "${2:-50}" -f "$LOG" ;;
  *)       die "usage: $0 [run|start|stop|restart|status|logs]" ;;
esac
