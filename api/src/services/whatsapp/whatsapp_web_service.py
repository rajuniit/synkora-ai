"""WhatsApp Web device-link service using neonize (Whatsmeow Python bindings).

Session state is stored in Redis so all API pods share the same view.
The neonize client (background thread + SQLite temp file) is pod-local,
but status, QR image, phone number, and the serialised session DB are
written to Redis as soon as they are available.  This means start_session,
stream/status polling, and save can all be served by different pods without
sticky routing.
"""

import base64
import io
import json
import logging
import re
import shutil
import tempfile
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

# Possible event names across neonize versions
_CONNECTED_EV_CANDIDATES = ["ConnectedEv", "ConnectedEvent", "PairSuccessEv"]
_HISTORY_SYNC_EV_CANDIDATES = ["HistorySyncEv", "HistorySyncEvent"]
_LOGGED_OUT_EV_CANDIDATES = ["LoggedOutEv", "LoggedOutEvent"]

# Log substrings that indicate a successful pairing (used as fallback connected detection)
_CONNECTED_LOG_SIGNALS = ("Pair success", "pair success", "Successfully paired", "Logged in as")

# Log substrings that are high-volume / noisy and should be suppressed during a session
_NOISE_PATTERNS = (
    "HistorySync",
    "history sync",
    "Inserting message",
    "Storing message",
    "Got history",
    "Decrypting history",
)


class _NeonizeNoiseFilter(logging.Filter):
    """
    Attached to the root logger during a QR session to suppress known
    high-volume neonize history-sync noise from ALL handlers (console, etc.).
    Removed when the session thread exits.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
            if any(p in msg for p in _NOISE_PATTERNS):
                return False  # drop this record
        except Exception:
            pass
        return True


class _NeonizeQRLogCapture(logging.Handler):
    """
    Intercepts neonize's internal Go-bridge logger to:
      - Capture QR code strings  (→ on_qr_fn)
      - Detect pair-success as a fallback connected signal (→ on_connected_fn)

    neonize emits QR codes through its Go goroutine and logs them as:
        "Emitting QR code <comma-separated-qr-string>"

    The Python event dispatcher (@client.event) is NOT called for QR events in
    neonize 0.3.x — only the Go-level logger fires. This handler bridges that gap.
    """

    def __init__(self, on_qr_fn, on_connected_fn=None):
        super().__init__(level=logging.DEBUG)
        self._on_qr_fn = on_qr_fn
        self._on_connected_fn = on_connected_fn
        self._seen: set[str] = set()
        self._connected_fired = False

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = record.getMessage()

            if "Emitting QR code" in msg:
                parts = msg.split("Emitting QR code ", 1)
                if len(parts) > 1:
                    qr_string = parts[1].strip()
                    if qr_string and qr_string not in self._seen:
                        self._seen.add(qr_string)
                        self._on_qr_fn(qr_string)

            # Fallback: detect pair success from Go-bridge log
            if self._on_connected_fn and not self._connected_fired:
                if any(sig in msg for sig in _CONNECTED_LOG_SIGNALS):
                    self._connected_fired = True
                    self._on_connected_fn()

        except Exception:
            pass  # log handlers must never raise


class WhatsAppWebService:
    """
    Manages WhatsApp Web QR linking sessions across multiple pods.

    Session state is split into two layers:
      - Redis (shared):  status, qr_data, phone_number, session_db_b64
        Any pod can read/write this, so SSE polling and the save endpoint
        work regardless of which pod started the session.
      - Pod-local (_local): neonize client object + temp session_dir
        These are OS resources that cannot be serialised; only the pod
        that called start_session holds them.

    TTL: Redis keys expire after _REDIS_TTL seconds (10 min).  This covers
    the 5-min QR window plus buffer, and auto-cleans abandoned sessions.
    """

    # Pod-local resources only — NOT shared across pods.
    # { session_id -> {client, session_dir} }
    _local: dict[str, dict] = {}

    _REDIS_PREFIX = "wa_qr_session:"
    _REDIS_TTL = 600  # 10 minutes

    @classmethod
    def send_text_message(cls, session_id: str, to_phone: str, text: str) -> bool:
        """
        Send a plain-text WhatsApp message via a device-linked session.

        This is a synchronous call used from within async HITL service code.
        Returns True on success, False if the session is not available or
        if neonize is not installed.
        """
        local = cls._local.get(session_id)
        if not local:
            logger.warning(f"WhatsApp Web send_text_message: session {session_id} not found in pod-local store")
            return False

        try:
            import neonize  # type: ignore[import]

            client = local.get("client")
            if client is None:
                logger.warning(f"WhatsApp Web send_text_message: no neonize client for session {session_id}")
                return False

            # Normalise phone number to JID format expected by neonize
            jid = to_phone.lstrip("+").replace(" ", "") + "@s.whatsapp.net"
            client.send_message(jid, neonize.proto.Message(conversation=text))
            return True
        except Exception as exc:
            logger.error(f"WhatsApp Web send_text_message failed for {to_phone}: {exc}", exc_info=True)
            return False

    # ------------------------------------------------------------------
    # Redis helpers
    # ------------------------------------------------------------------

    @classmethod
    def _rkey(cls, session_id: str) -> str:
        return f"{cls._REDIS_PREFIX}{session_id}"

    @classmethod
    def _redis_write(cls, session_id: str, data: dict) -> None:
        """Overwrite the full session doc in Redis."""
        try:
            from ...config.redis import get_redis

            r = get_redis()
            if r:
                r.setex(cls._rkey(session_id), cls._REDIS_TTL, json.dumps(data))
        except Exception:
            logger.warning(f"Redis write failed for QR session {session_id}", exc_info=True)

    @classmethod
    def _redis_patch(cls, session_id: str, **fields) -> None:
        """Atomically patch specific fields in the Redis session doc."""
        try:
            from ...config.redis import get_redis

            r = get_redis()
            if r:
                raw = r.get(cls._rkey(session_id))
                current: dict = json.loads(raw) if raw else {}
                current.update(fields)
                r.setex(cls._rkey(session_id), cls._REDIS_TTL, json.dumps(current))
        except Exception:
            logger.warning(f"Redis patch failed for QR session {session_id}", exc_info=True)

    @classmethod
    def _redis_read(cls, session_id: str) -> dict | None:
        """Return the session doc from Redis, or None if not found."""
        try:
            from ...config.redis import get_redis

            r = get_redis()
            if r:
                raw = r.get(cls._rkey(session_id))
                if raw:
                    return json.loads(raw)
        except Exception:
            logger.warning(f"Redis read failed for QR session {session_id}", exc_info=True)
        return None

    @classmethod
    def _redis_delete(cls, session_id: str) -> None:
        try:
            from ...config.redis import get_redis

            r = get_redis()
            if r:
                r.delete(cls._rkey(session_id))
        except Exception:
            logger.warning(f"Redis delete failed for QR session {session_id}", exc_info=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @classmethod
    async def start_session(cls, session_id: str) -> None:
        """
        Start a new QR linking session.

        Launches a background thread running the neonize client on this pod.
        QR codes and connection state are published to Redis so that any pod
        can serve subsequent status/stream/save requests.
        """
        try:
            import neonize.events as neonize_events  # type: ignore[import]
            from neonize.client import NewClient  # type: ignore[import]
        except Exception as exc:
            logger.error(f"neonize import failed — {type(exc).__name__}: {exc}", exc_info=True)
            raise RuntimeError(f"neonize failed to load: {type(exc).__name__}: {exc}") from exc

        # Discover event classes dynamically (names vary across neonize minor versions)
        def _find_ev(candidates):
            for name in candidates:
                ev = getattr(neonize_events, name, None)
                if ev is not None:
                    return ev, name
            return None, None

        connected_ev, connected_ev_name = _find_ev(_CONNECTED_EV_CANDIDATES)
        history_sync_ev, _ = _find_ev(_HISTORY_SYNC_EV_CANDIDATES)
        logged_out_ev, _ = _find_ev(_LOGGED_OUT_EV_CANDIDATES)

        if connected_ev_name:
            logger.info(f"neonize connected event class resolved: {connected_ev_name}")

        session_dir = tempfile.mkdtemp(prefix=f"neonize_{session_id}_")
        db_path = str(Path(session_dir) / "session.db")

        # Initialise shared state in Redis (visible to all pods immediately)
        cls._redis_write(
            session_id,
            {
                "status": "pending",
                "qr_data": None,
                "phone_number": None,
                "session_db_b64": None,
            },
        )

        # Track pod-local resources (not shared)
        cls._local[session_id] = {"client": None, "session_dir": session_dir}

        def _handle_qr(qr_string: str) -> None:
            """Render a QR string to a base64 PNG and publish to Redis."""
            try:
                import qrcode  # type: ignore[import]

                logger.info(f"Rendering QR image for session {session_id}")
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_L,
                    box_size=10,
                    border=4,
                )
                qr.add_data(qr_string)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                qr_b64 = base64.b64encode(buf.getvalue()).decode()
                cls._redis_patch(session_id, status="qr_ready", qr_data=qr_b64)
                logger.info(f"QR code ready for session {session_id}")
            except Exception:
                logger.exception(f"Failed to render QR image for session {session_id}")

        def _extract_phone(jid) -> str | None:
            """
            Extract a plain phone number string from a neonize JID object.

            neonize JID objects are protobuf messages.  str(jid) gives text like:
                User: "60179664801"
                RawAgent: 0
                Device: 19
                Server: "s.whatsapp.net"
                IsEmpty: false

            We try attribute access first (most reliable), then regex on the
            string representation as a fallback.
            """
            try:
                # Direct attribute access (protobuf field)
                user = getattr(jid, "User", None)
                if user and str(user) not in ("", "0", "None"):
                    raw = str(user)
                    return f"+{raw}" if not raw.startswith("+") else raw
            except Exception:
                pass
            try:
                # Regex fallback — parse `User: "DIGITS"` from the text representation
                match = re.search(r'User:\s*"(\d+)"', str(jid))
                if match:
                    raw = match.group(1)
                    return f"+{raw}" if not raw.startswith("+") else raw
            except Exception:
                pass
            return None

        def _handle_connected(cli) -> None:
            """
            Extract phone number, serialise the neonize SQLite session to Redis,
            and mark the session connected.  All written atomically so any pod
            can serve the save endpoint immediately after this fires.
            """
            # Guard: only fire once
            current = cls._redis_read(session_id) or {}
            if current.get("status") == "connected":
                return

            phone = None
            try:
                me = cli.get_me()
                jid = getattr(me, "JID", me)
                phone = _extract_phone(jid)
                if phone:
                    logger.info(f"Session {session_id} connected as {phone}")
                else:
                    logger.warning(
                        f"Could not extract phone number for session {session_id} (will still mark connected)"
                    )
            except Exception:
                logger.warning(f"get_me() failed for session {session_id} (will still mark connected)")

            # Serialise the SQLite session file → base64 → Redis so any pod can
            # retrieve it when the user calls the save endpoint.
            session_db_b64 = None
            try:
                db_file = Path(db_path)
                if db_file.exists():
                    session_db_b64 = base64.b64encode(db_file.read_bytes()).decode()
            except Exception:
                logger.exception(f"Failed to serialise session DB for {session_id}")

            cls._redis_patch(session_id, status="connected", phone_number=phone, session_db_b64=session_db_b64)

        def _handle_connected_log_fallback() -> None:
            """Called when the Go-bridge logger reports pair success (fallback path)."""
            current = cls._redis_read(session_id) or {}
            if current.get("status") == "connected":
                return
            logger.info(f"Session {session_id} connected via log-fallback (phone unknown)")
            cls._redis_patch(session_id, status="connected")

        def _run_client() -> None:
            """Background thread: installs QR log capture + noise filter, runs neonize, cleans up."""
            root_logger = logging.getLogger()
            qr_capture = _NeonizeQRLogCapture(_handle_qr, on_connected_fn=_handle_connected_log_fallback)
            root_logger.addHandler(qr_capture)
            noise_filter = _NeonizeNoiseFilter()
            root_logger.addFilter(noise_filter)

            try:
                client = NewClient(db_path)
                if session_id in cls._local:
                    cls._local[session_id]["client"] = client

                if connected_ev is not None:

                    @client.event(connected_ev)
                    def _on_connected(cli, evt) -> None:  # noqa: ARG001
                        _handle_connected(cli)

                if history_sync_ev is not None:

                    @client.event(history_sync_ev)
                    def _on_history_sync(cli, evt) -> None:  # noqa: ARG001
                        pass  # suppress default behaviour / logging

                if logged_out_ev is not None:

                    @client.event(logged_out_ev)
                    def _on_logged_out(cli, evt) -> None:  # noqa: ARG001
                        logger.info(f"Session {session_id} received LoggedOut event")
                        cls._redis_patch(session_id, status="disconnected")

                client.connect()

            except Exception:
                logger.exception(f"Neonize client error for session {session_id}")
                cls._redis_patch(session_id, status="disconnected")
            finally:
                root_logger.removeHandler(qr_capture)
                root_logger.removeFilter(noise_filter)
                # Clean up pod-local temp dir; Redis entry expires on its own TTL
                local = cls._local.pop(session_id, None)
                if local:
                    session_dir_ = local.get("session_dir")
                    if session_dir_:
                        shutil.rmtree(session_dir_, ignore_errors=True)
                logger.info(f"Neonize thread exited for session {session_id}")

        thread = threading.Thread(target=_run_client, daemon=True, name=f"neonize-{session_id[:8]}")
        thread.start()

    @classmethod
    def get_qr_data(cls, session_id: str) -> str | None:
        """Return the current QR code as a base64-encoded PNG string, or None."""
        data = cls._redis_read(session_id)
        return data.get("qr_data") if data else None

    @classmethod
    def get_status(cls, session_id: str) -> str:
        """
        Return the current session status (reads from Redis — works on any pod).

        Values: pending | qr_ready | scanning | connected | disconnected | not_found
        """
        data = cls._redis_read(session_id)
        if data is None:
            return "not_found"
        return data.get("status", "not_found")

    @classmethod
    def get_phone_number(cls, session_id: str) -> str | None:
        """Return the connected phone number, or None if not yet connected."""
        data = cls._redis_read(session_id)
        return data.get("phone_number") if data else None

    @classmethod
    async def stop_session(cls, session_id: str) -> None:
        """
        Cancel a QR session.

        Deletes the Redis key (visible to all pods immediately) and disconnects
        the local neonize client if this pod happens to own it.  If this pod
        does not own the session, the neonize thread on the owning pod will
        detect the Redis key is gone on its next write and clean up naturally.
        """
        cls._redis_delete(session_id)

        local = cls._local.pop(session_id, None)
        if local is None:
            return

        client = local.get("client")
        if client is not None:
            try:
                client.disconnect()
            except Exception:
                logger.debug(f"Error disconnecting neonize client for session {session_id}", exc_info=True)

        session_dir = local.get("session_dir")
        if session_dir:
            try:
                shutil.rmtree(session_dir, ignore_errors=True)
            except Exception:
                logger.debug(f"Failed to clean up session dir for {session_id}", exc_info=True)

    @classmethod
    def get_session_data(cls, session_id: str) -> str | None:
        """
        Return serialised session data for DB persistence (reads from Redis).

        The neonize SQLite bytes are base64-encoded into Redis by _handle_connected
        on the pod that owns the neonize thread, so this works on any pod.
        The caller is responsible for encrypting the result before storing it.
        """
        data = cls._redis_read(session_id)
        if not data:
            return None
        session_db_b64 = data.get("session_db_b64")
        if not session_db_b64:
            return None
        return json.dumps(
            {
                "session_db": session_db_b64,
                "phone_number": data.get("phone_number"),
            }
        )
