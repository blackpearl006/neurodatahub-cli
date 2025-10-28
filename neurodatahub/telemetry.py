"""Privacy-first telemetry tracking for NeuroDataHub CLI.

This module implements opt-in telemetry that records anonymized download events.
NO personally identifiable information (PII) is collected:
- No IP addresses, usernames, emails, local paths, or hostnames
- Ephemeral session IDs are generated per CLI invocation (not persisted)
- All network calls fail silently if they encounter errors

Data collected:
- Dataset ID, success/failure status, metadata received status
- Resume attempt counts, optional user-provided notes
- OS platform, Python version, CLI version
- Ephemeral session ID (per-run, not persistent)
"""

import platform
import sys
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional

import requests

from . import __version__
from .logging_config import get_logger
from .state import get_state_manager

logger = get_logger(__name__)

# Telemetry endpoint (Google Apps Script)
DEFAULT_TELEMETRY_ENDPOINT = (
    "https://script.google.com/macros/s/AKfycbxvtanEmHq2UMUExNo5ELIy1qm0JSt9nRsaqNnFE9PwHHlRp-FDp7JDGlM8FijDkiHE/exec"
)

# Rate limiting: max 10 events per minute (tracked in-memory)
_event_timestamps: List[float] = []
MAX_EVENTS_PER_MINUTE = 10
RATE_LIMIT_WINDOW = 60  # seconds

# Session ID: generated once per CLI invocation, not persisted
_session_id: Optional[str] = None


def _get_session_id() -> str:
    """Get or generate ephemeral session ID.

    Session ID is generated once per CLI invocation and stored in memory only.
    It is NOT persisted across runs.

    Returns:
        Ephemeral session ID (short UUID)
    """
    global _session_id
    if _session_id is None:
        _session_id = str(uuid.uuid4())[:8]
    return _session_id


def _is_rate_limited() -> bool:
    """Check if we're currently rate limited.

    Rate limit: max 10 events per 60 seconds.

    Returns:
        True if rate limited, False otherwise
    """
    global _event_timestamps
    current_time = time.time()

    # Remove timestamps older than the window
    _event_timestamps = [
        ts for ts in _event_timestamps if current_time - ts < RATE_LIMIT_WINDOW
    ]

    if len(_event_timestamps) >= MAX_EVENTS_PER_MINUTE:
        logger.debug(
            f"Rate limit exceeded: {len(_event_timestamps)} events in last minute"
        )
        return True

    return False


def _record_event_timestamp() -> None:
    """Record timestamp of current event for rate limiting."""
    global _event_timestamps
    _event_timestamps.append(time.time())


def _get_system_info() -> Dict[str, str]:
    """Get anonymized system information.

    Returns:
        Dictionary with OS, Python version, CLI version
    """
    return {
        "os": platform.system(),  # e.g., "Linux", "Darwin", "Windows"
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "cli_version": __version__,
    }


def _build_download_event_payload(
    dataset_name: str,
    succeeded: bool,
    metadata_received: bool,
    resume_attempts: int,
    note: Optional[str] = None,
) -> Dict:
    """Build payload for download event.

    Args:
        dataset_name: Dataset identifier
        succeeded: Whether download succeeded
        metadata_received: Whether metadata was successfully retrieved
        resume_attempts: Number of resume attempts
        note: Optional user-provided note/description

    Returns:
        Event payload dictionary
    """
    payload = {
        "type": "download",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "dataset": dataset_name,
        "succeeded": succeeded,
        "metadata_received": metadata_received,
        "resume_attempts": resume_attempts,
        "session_id": _get_session_id(),
    }

    # Add system info
    payload.update(_get_system_info())

    # Add optional note
    if note:
        payload["placeholder_description"] = note

    return payload


def _send_telemetry_event(
    payload: Dict, endpoint: Optional[str] = None, timeout: int = 3
) -> bool:
    """Send telemetry event to backend (fire-and-forget).

    Args:
        payload: Event payload dictionary
        endpoint: Optional custom endpoint URL
        timeout: Request timeout in seconds (default: 3)

    Returns:
        True if send succeeded, False otherwise
    """
    endpoint = endpoint or DEFAULT_TELEMETRY_ENDPOINT

    try:
        response = requests.post(
            endpoint,
            json=payload,
            timeout=timeout,
            headers={"Content-Type": "application/json"},
        )

        if response.status_code == 200:
            logger.debug("Telemetry event sent successfully")
            return True
        elif response.status_code == 429:
            logger.debug("Telemetry backend rate limit exceeded")
            return False
        else:
            logger.debug(f"Telemetry send failed with status {response.status_code}")
            return False

    except requests.exceptions.Timeout:
        logger.debug("Telemetry request timed out (this is expected, continuing...)")
        return False
    except requests.exceptions.RequestException as e:
        logger.debug(f"Telemetry request failed: {e} (continuing...)")
        return False
    except Exception as e:
        logger.debug(f"Unexpected error sending telemetry: {e} (continuing...)")
        return False


def record_download_event(
    dataset_name: str,
    succeeded: bool,
    metadata_received: bool = True,
    resume_attempts: int = 0,
    note: Optional[str] = None,
    endpoint: Optional[str] = None,
) -> None:
    """Record a download event with telemetry.

    This function:
    1. Increments local counters in state.json (always, regardless of consent)
    2. If user consented, sends anonymized event to telemetry backend
    3. All network failures are silent (fire-and-forget semantics)

    Args:
        dataset_name: Dataset identifier
        succeeded: Whether download succeeded
        metadata_received: Whether metadata was successfully retrieved
        resume_attempts: Number of resume attempts
        note: Optional user-provided note/description
        endpoint: Optional custom telemetry endpoint
    """
    state_manager = get_state_manager()

    # Always increment local counters (regardless of telemetry consent)
    if succeeded:
        state_manager.increment_successful_run(dataset_name)
    else:
        state_manager.increment_failed_run(dataset_name)

    # Only send telemetry if user consented
    if not state_manager.has_telemetry_consent():
        logger.debug("Telemetry not consented, skipping event send")
        return

    # Check rate limit
    if _is_rate_limited():
        logger.debug("Rate limited, skipping telemetry event")
        return

    # Build and send event
    try:
        payload = _build_download_event_payload(
            dataset_name, succeeded, metadata_received, resume_attempts, note
        )

        success = _send_telemetry_event(payload, endpoint)

        if success:
            _record_event_timestamp()

    except Exception as e:
        # Fail silently - telemetry should never break the CLI
        logger.debug(f"Error in record_download_event: {e} (continuing...)")


def get_telemetry_status() -> Dict[str, any]:
    """Get current telemetry status.

    Returns:
        Dictionary with telemetry configuration and statistics
    """
    state_manager = get_state_manager()

    return {
        "consent_given": state_manager.has_telemetry_consent(),
        "consent_asked": state_manager.was_telemetry_consent_asked(),
        "successful_runs": state_manager.get_successful_runs(),
        "failed_runs": state_manager.get_failed_runs(),
        "endpoint": DEFAULT_TELEMETRY_ENDPOINT,
        "session_id": _get_session_id(),
    }
