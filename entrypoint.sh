#!/usr/bin/env bash
#
# Container entrypoint — starts uvicorn and Streamlit together and exits the
# container as soon as either process dies, so Docker / the orchestrator can
# restart cleanly instead of leaving a half-broken deployment running.
#
# Fixes addressed:
#   Mode A — uvicorn crash no longer leaves the container alive with a dead API.
#   Mode C — Streamlit starts only after uvicorn is confirmed ready, avoiding
#             connection-refused errors for the first user on a cold start.
#   Mode D — SIGTERM from "docker stop" is caught by the trap and forwarded to
#             both child processes, allowing graceful in-flight request draining.

set -u

export API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:${PORT:-8000}}"

# ---------------------------------------------------------------------------
# Start uvicorn in the background and record its PID.
# ---------------------------------------------------------------------------
uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}" &
UVICORN_PID=$!

# STREAMLIT_PID is set later; declare it empty so the trap can reference it
# safely even if the script exits before Streamlit starts.
STREAMLIT_PID=""

# ---------------------------------------------------------------------------
# Cleanup — kill both children and wait for them to finish.
# Registered on EXIT so it runs regardless of how the script terminates
# (wait -n returning, SIGTERM from "docker stop", unhandled error, etc.).
# ---------------------------------------------------------------------------
_cleanup() {
    kill "${UVICORN_PID}" ${STREAMLIT_PID:+"${STREAMLIT_PID}"} 2>/dev/null
    wait
}
trap _cleanup EXIT SIGTERM SIGINT

# ---------------------------------------------------------------------------
# Mode C fix: wait for uvicorn to bind before starting Streamlit.
# Mirrors the existing HEALTHCHECK so we reuse the same Python one-liner.
# Gives up after 30 s — if uvicorn is still down then, "wait -n" below will
# detect that it has exited and the container will exit immediately.
# ---------------------------------------------------------------------------
TRIES=30
until python -c "
import urllib.request, sys
try:
    urllib.request.urlopen(
        'http://127.0.0.1:${PORT:-8000}/health', timeout=2
    )
except Exception:
    sys.exit(1)
" 2>/dev/null || [ "${TRIES}" -eq 0 ]; do
    TRIES=$((TRIES - 1))
    sleep 1
done

# ---------------------------------------------------------------------------
# Start Streamlit in the background and record its PID.
# ---------------------------------------------------------------------------
streamlit run frontend/app.py \
    --server.address 0.0.0.0 \
    --server.port "${STREAMLIT_PORT:-8501}" \
    --server.headless true \
    --browser.gatherUsageStats false &
STREAMLIT_PID=$!

# ---------------------------------------------------------------------------
# Mode A fix: block until EITHER child exits.
# "wait -n" returns the exit code of whichever process died first.
# Reaching this point triggers the EXIT trap, which kills the survivor.
# ---------------------------------------------------------------------------
wait -n "${UVICORN_PID}" "${STREAMLIT_PID}"
