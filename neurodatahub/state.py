"""State management for NeuroDataHub CLI telemetry and feedback tracking.

This module manages persistent local state stored in ~/.neurodatahub/state.json.
State includes download counters, telemetry consent status, and feedback tracking.
All operations are atomic and thread-safe.
"""

import copy
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from .logging_config import get_logger

logger = get_logger(__name__)


class StateManager:
    """Manages persistent local state for telemetry and feedback tracking.

    State file location: ~/.neurodatahub/state.json

    State schema:
    {
        "successful_runs": int,
        "failed_runs": int,
        "per_dataset": {
            "dataset_id": {"success": int, "fail": int},
            ...
        },
        "last_feedback_run_count": int,
        "telemetry_consent_given": bool,
        "telemetry_consent_asked": bool
    }
    """

    DEFAULT_STATE = {
        "successful_runs": 0,
        "failed_runs": 0,
        "per_dataset": {},
        "last_feedback_run_count": 0,
        "telemetry_consent_given": False,
        "telemetry_consent_asked": False,
        "last_privacy_notice_shown": None,  # ISO timestamp, None if never shown
        "feedback_consent_given": False,  # Implicit consent for feedback
    }

    def __init__(self, state_file: Optional[Path] = None):
        """Initialize state manager.

        Args:
            state_file: Path to state file. If None, uses ~/.neurodatahub/state.json
        """
        self.state_file = state_file or self._get_default_state_file()
        self._ensure_state_dir()

        # In-memory only: current download log path (not persisted to state.json)
        self._current_download_log_path: Optional[str] = None

    def _get_default_state_file(self) -> Path:
        """Get default state file path."""
        return Path.home() / ".neurodatahub" / "state.json"

    def _ensure_state_dir(self) -> None:
        """Ensure state directory exists."""
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning(f"Could not create state directory: {e}")

    def _acquire_lock(self, file_obj):
        """Acquire exclusive lock on file (platform-specific)."""
        if sys.platform == "win32":
            try:
                import msvcrt

                msvcrt.locking(file_obj.fileno(), msvcrt.LK_LOCK, 1)
            except ImportError:
                logger.debug("msvcrt not available, skipping file lock")
            except Exception as e:
                logger.debug(f"Could not acquire lock: {e}")
        else:
            try:
                import fcntl

                fcntl.flock(file_obj.fileno(), fcntl.LOCK_EX)
            except ImportError:
                logger.debug("fcntl not available, skipping file lock")
            except Exception as e:
                logger.debug(f"Could not acquire lock: {e}")

    def _release_lock(self, file_obj):
        """Release lock on file (platform-specific)."""
        if sys.platform == "win32":
            try:
                import msvcrt

                msvcrt.locking(file_obj.fileno(), msvcrt.LK_UNLCK, 1)
            except Exception as e:
                logger.debug(f"Could not release lock: {e}")
        else:
            try:
                import fcntl

                fcntl.flock(file_obj.fileno(), fcntl.LOCK_UN)
            except Exception as e:
                logger.debug(f"Could not release lock: {e}")

    def load_state(self) -> Dict[str, Any]:
        """Load state from file with atomic operations.

        Returns:
            State dictionary. Returns default state if file doesn't exist or is invalid.
        """
        if not self.state_file.exists():
            logger.debug("State file does not exist, using default state")
            return copy.deepcopy(self.DEFAULT_STATE)

        try:
            with open(self.state_file, "r") as f:
                self._acquire_lock(f)
                try:
                    state = json.load(f)
                    # Merge with default state to ensure all keys exist
                    merged_state = copy.deepcopy(self.DEFAULT_STATE)
                    merged_state.update(state)
                    return merged_state
                finally:
                    self._release_lock(f)
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in state file: {e}, using default state")
            return copy.deepcopy(self.DEFAULT_STATE)
        except Exception as e:
            logger.warning(f"Error loading state: {e}, using default state")
            return copy.deepcopy(self.DEFAULT_STATE)

    def save_state(self, state: Dict[str, Any]) -> bool:
        """Save state to file atomically.

        Args:
            state: State dictionary to save

        Returns:
            True if save succeeded, False otherwise
        """
        try:
            # Write to temporary file first
            temp_file = self.state_file.with_suffix(".json.tmp")

            with open(temp_file, "w") as f:
                self._acquire_lock(f)
                try:
                    json.dump(state, f, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                finally:
                    self._release_lock(f)

            # Atomic rename
            temp_file.replace(self.state_file)
            logger.debug("State saved successfully")
            return True

        except Exception as e:
            logger.error(f"Error saving state: {e}")
            # Clean up temp file if it exists
            try:
                if temp_file.exists():
                    temp_file.unlink()
            except Exception:
                pass
            return False

    def increment_successful_run(self, dataset_id: Optional[str] = None) -> None:
        """Increment successful run counter.

        Args:
            dataset_id: Optional dataset ID to also increment per-dataset counter
        """
        state = self.load_state()
        state["successful_runs"] += 1

        if dataset_id:
            if dataset_id not in state["per_dataset"]:
                state["per_dataset"][dataset_id] = {"success": 0, "fail": 0}
            state["per_dataset"][dataset_id]["success"] += 1

        self.save_state(state)
        logger.debug(f"Incremented successful runs to {state['successful_runs']}")

    def increment_failed_run(self, dataset_id: Optional[str] = None) -> None:
        """Increment failed run counter.

        Args:
            dataset_id: Optional dataset ID to also increment per-dataset counter
        """
        state = self.load_state()
        state["failed_runs"] += 1

        if dataset_id:
            if dataset_id not in state["per_dataset"]:
                state["per_dataset"][dataset_id] = {"success": 0, "fail": 0}
            state["per_dataset"][dataset_id]["fail"] += 1

        self.save_state(state)
        logger.debug(f"Incremented failed runs to {state['failed_runs']}")

    def get_successful_runs(self) -> int:
        """Get total successful runs count.

        Returns:
            Number of successful runs
        """
        state = self.load_state()
        return state.get("successful_runs", 0)

    def get_failed_runs(self) -> int:
        """Get total failed runs count.

        Returns:
            Number of failed runs
        """
        state = self.load_state()
        return state.get("failed_runs", 0)

    def get_dataset_stats(self, dataset_id: str) -> Dict[str, int]:
        """Get statistics for a specific dataset.

        Args:
            dataset_id: Dataset identifier

        Returns:
            Dictionary with "success" and "fail" counts
        """
        state = self.load_state()
        per_dataset = state.get("per_dataset", {})
        return per_dataset.get(dataset_id, {"success": 0, "fail": 0})

    def set_telemetry_consent(self, consented: bool) -> None:
        """Set telemetry consent status.

        Args:
            consented: Whether user consented to telemetry
        """
        state = self.load_state()
        state["telemetry_consent_given"] = consented
        state["telemetry_consent_asked"] = True
        self.save_state(state)
        logger.info(f"Telemetry consent set to: {consented}")

    def has_telemetry_consent(self) -> bool:
        """Check if user has given telemetry consent.

        Returns:
            True if user consented, False otherwise
        """
        state = self.load_state()
        return state.get("telemetry_consent_given", False)

    def was_telemetry_consent_asked(self) -> bool:
        """Check if telemetry consent was already asked.

        Returns:
            True if consent was asked before, False otherwise
        """
        state = self.load_state()
        return state.get("telemetry_consent_asked", False)

    def update_last_feedback_run_count(self, run_count: int) -> None:
        """Update the run count when feedback was last shown.

        Args:
            run_count: Run count when feedback was shown
        """
        state = self.load_state()
        state["last_feedback_run_count"] = run_count
        self.save_state(state)
        logger.debug(f"Updated last feedback run count to {run_count}")

    def get_last_feedback_run_count(self) -> int:
        """Get the run count when feedback was last shown.

        Returns:
            Last feedback run count
        """
        state = self.load_state()
        return state.get("last_feedback_run_count", 0)

    def reset_state(self) -> None:
        """Reset state to default values."""
        self.save_state(copy.deepcopy(self.DEFAULT_STATE))
        logger.info("State reset to defaults")

    def should_show_privacy_notice(self, days_threshold: int = 100) -> bool:
        """Check if privacy notice should be shown based on threshold.

        Args:
            days_threshold: Number of days before re-showing notice (default: 100)

        Returns:
            True if notice should be shown, False otherwise
        """
        from datetime import datetime

        state = self.load_state()
        last_shown = state.get("last_privacy_notice_shown")

        if last_shown is None:
            return True

        try:
            last_shown_dt = datetime.fromisoformat(last_shown.replace("Z", "+00:00"))
            days_since = (datetime.utcnow() - last_shown_dt.replace(tzinfo=None)).days
            return days_since >= days_threshold
        except (ValueError, AttributeError):
            # Invalid timestamp, show notice
            return True

    def mark_privacy_notice_shown(self) -> None:
        """Mark that privacy notice was shown (current timestamp)."""
        from datetime import datetime

        state = self.load_state()
        state["last_privacy_notice_shown"] = datetime.utcnow().isoformat() + "Z"
        self.save_state(state)
        logger.debug("Marked privacy notice as shown")

    def set_feedback_consent(self, consented: bool) -> None:
        """Set feedback consent status (implicit consent).

        Args:
            consented: Whether user gave implicit consent for feedback
        """
        state = self.load_state()
        state["feedback_consent_given"] = consented
        self.save_state(state)
        logger.debug(f"Feedback consent set to: {consented}")

    def has_feedback_consent(self) -> bool:
        """Check if user has given feedback consent.

        Returns:
            True if user consented, False otherwise
        """
        state = self.load_state()
        return state.get("feedback_consent_given", False)

    def set_current_download_log_path(self, log_path: Optional[str]) -> None:
        """Set the current download log path (in-memory only).

        Args:
            log_path: Path to the current download log file
        """
        self._current_download_log_path = log_path
        logger.debug(f"Set current download log path: {log_path}")

    def get_current_download_log_path(self) -> Optional[str]:
        """Get the current download log path (in-memory only).

        Returns:
            Path to current download log file, or None
        """
        return self._current_download_log_path


# Global state manager instance
_state_manager_instance: Optional[StateManager] = None


def get_state_manager() -> StateManager:
    """Get the global state manager instance.

    Returns:
        StateManager instance
    """
    global _state_manager_instance
    if _state_manager_instance is None:
        _state_manager_instance = StateManager()
    return _state_manager_instance
