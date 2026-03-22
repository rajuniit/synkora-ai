"""WhatsApp Web device-link service using neonize (Whatsmeow Python bindings)."""

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
    Manages in-memory WhatsApp Web QR linking sessions.

    Each session lives in memory while QR scanning is in progress.
    On successful connection the session_data can be retrieved for
    encrypted persistence to the database.
    """

    # session_id -> {status, qr_data, phone_number, client, session_dir}
    _sessions: dict[str, dict] = {}

    @classmethod
    async def start_session(cls, session_id: str) -> None:
        """
        Start a new QR linking session.

        Launches a background thread running the neonize client.
        QR codes are captured via the Go-bridge log and status is updated
        in _sessions[session_id].
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

        cls._sessions[session_id] = {
            "status": "pending",
            "qr_data": None,
            "phone_number": None,
            "client": None,
            "session_dir": session_dir,
        }

        def _handle_qr(qr_string: str) -> None:
            """Render a QR string to a base64 PNG and store it in the session."""
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
                cls._sessions[session_id]["qr_data"] = base64.b64encode(buf.getvalue()).decode()
                cls._sessions[session_id]["status"] = "qr_ready"
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
            """Extract the linked phone number and mark the session connected."""
            # Guard: only fire once
            if cls._sessions.get(session_id, {}).get("status") == "connected":
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
            if session_id in cls._sessions:
                cls._sessions[session_id]["phone_number"] = phone
                cls._sessions[session_id]["status"] = "connected"

        def _handle_connected_log_fallback() -> None:
            """Called when the Go-bridge logger reports pair success (fallback path)."""
            if cls._sessions.get(session_id, {}).get("status") == "connected":
                return
            logger.info(f"Session {session_id} connected via log-fallback (phone unknown)")
            if session_id in cls._sessions:
                cls._sessions[session_id]["status"] = "connected"

        def _run_client() -> None:
            """Background thread: installs QR log capture + noise filter, runs neonize, cleans up."""
            root_logger = logging.getLogger()
            # Handler: captures QR strings and pair-success signals from Go-bridge log
            qr_capture = _NeonizeQRLogCapture(_handle_qr, on_connected_fn=_handle_connected_log_fallback)
            root_logger.addHandler(qr_capture)
            # Filter: drops known high-volume neonize noise from ALL handlers (console, etc.)
            noise_filter = _NeonizeNoiseFilter()
            root_logger.addFilter(noise_filter)

            try:
                client = NewClient(db_path)
                cls._sessions[session_id]["client"] = client

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
                        if session_id in cls._sessions:
                            cls._sessions[session_id]["status"] = "disconnected"

                client.connect()

            except Exception:
                logger.exception(f"Neonize client error for session {session_id}")
                if session_id in cls._sessions:
                    cls._sessions[session_id]["status"] = "disconnected"
            finally:
                root_logger.removeHandler(qr_capture)
                root_logger.removeFilter(noise_filter)

        thread = threading.Thread(target=_run_client, daemon=True, name=f"neonize-{session_id[:8]}")
        thread.start()

    @classmethod
    def get_qr_data(cls, session_id: str) -> str | None:
        """Return the current QR code as a base64-encoded PNG string, or None."""
        session = cls._sessions.get(session_id)
        return session["qr_data"] if session else None

    @classmethod
    def get_status(cls, session_id: str) -> str:
        """
        Return the current session status.

        Values: pending | qr_ready | scanning | connected | disconnected | not_found
        """
        session = cls._sessions.get(session_id)
        if session is None:
            return "not_found"
        return session["status"]

    @classmethod
    def get_phone_number(cls, session_id: str) -> str | None:
        """Return the connected phone number, or None if not yet connected."""
        session = cls._sessions.get(session_id)
        return session["phone_number"] if session else None

    @classmethod
    async def stop_session(cls, session_id: str) -> None:
        """Disconnect the client and remove the session from memory."""
        session = cls._sessions.pop(session_id, None)
        if session is None:
            return

        client = session.get("client")
        if client is not None:
            try:
                client.disconnect()
            except Exception:
                logger.debug(f"Error disconnecting neonize client for session {session_id}", exc_info=True)

        session_dir = session.get("session_dir")
        if session_dir:
            try:
                shutil.rmtree(session_dir, ignore_errors=True)
            except Exception:
                logger.debug(f"Failed to clean up session dir for {session_id}", exc_info=True)

    @classmethod
    def get_session_data(cls, session_id: str) -> str | None:
        """
        Return serialised session data for DB persistence.

        Reads the neonize SQLite database, base64-encodes it, and returns it
        as a JSON string. The caller is responsible for encrypting the result.
        """
        session = cls._sessions.get(session_id)
        if session is None:
            return None

        session_dir = session.get("session_dir")
        if not session_dir:
            return None

        db_file = Path(session_dir) / "session.db"
        if db_file.exists():
            try:
                db_bytes = db_file.read_bytes()
                return json.dumps(
                    {
                        "session_db": base64.b64encode(db_bytes).decode(),
                        "phone_number": session.get("phone_number"),
                    }
                )
            except Exception:
                logger.exception(f"Failed to read session DB for {session_id}")

        return None
