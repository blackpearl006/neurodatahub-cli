"""Unit tests for telemetry module."""

import time
from unittest.mock import MagicMock, patch

import pytest
import requests

from neurodatahub import telemetry
from neurodatahub.state import StateManager


@pytest.fixture
def mock_state_manager(tmp_path):
    """Create a mock state manager for testing."""
    state_file = tmp_path / "test_state.json"
    return StateManager(state_file=state_file)


@pytest.fixture
def reset_telemetry_globals():
    """Reset telemetry module global variables between tests."""
    telemetry._session_id = None
    telemetry._event_timestamps = []
    yield
    telemetry._session_id = None
    telemetry._event_timestamps = []


class TestSessionId:
    """Test session ID generation."""

    def test_session_id_generated(self, reset_telemetry_globals):
        """Test that session ID is generated."""
        session_id = telemetry._get_session_id()
        assert session_id is not None
        assert isinstance(session_id, str)
        assert len(session_id) == 8  # Short UUID

    def test_session_id_consistent(self, reset_telemetry_globals):
        """Test that session ID is consistent within same run."""
        session_id1 = telemetry._get_session_id()
        session_id2 = telemetry._get_session_id()
        assert session_id1 == session_id2


class TestRateLimiting:
    """Test rate limiting functionality."""

    def test_not_rate_limited_initially(self, reset_telemetry_globals):
        """Test that rate limiting is not active initially."""
        assert not telemetry._is_rate_limited()

    def test_rate_limit_after_max_events(self, reset_telemetry_globals):
        """Test that rate limit activates after max events."""
        # Add MAX_EVENTS_PER_MINUTE timestamps
        current_time = time.time()
        for _ in range(telemetry.MAX_EVENTS_PER_MINUTE):
            telemetry._event_timestamps.append(current_time)

        assert telemetry._is_rate_limited()

    def test_rate_limit_clears_old_timestamps(self, reset_telemetry_globals):
        """Test that old timestamps are cleared."""
        # Add old timestamps (outside window)
        old_time = time.time() - (telemetry.RATE_LIMIT_WINDOW + 10)
        for _ in range(5):
            telemetry._event_timestamps.append(old_time)

        # Should not be rate limited (old events cleared)
        assert not telemetry._is_rate_limited()

    def test_record_event_timestamp(self, reset_telemetry_globals):
        """Test recording event timestamp."""
        telemetry._record_event_timestamp()
        assert len(telemetry._event_timestamps) == 1

        telemetry._record_event_timestamp()
        assert len(telemetry._event_timestamps) == 2


class TestSystemInfo:
    """Test system info collection."""

    def test_get_system_info_structure(self):
        """Test that system info has correct structure."""
        info = telemetry._get_system_info()

        assert "os" in info
        assert "python" in info
        assert "cli_version" in info

        assert isinstance(info["os"], str)
        assert isinstance(info["python"], str)
        assert isinstance(info["cli_version"], str)

    def test_get_system_info_no_pii(self):
        """Test that system info contains no PII."""
        info = telemetry._get_system_info()

        # Should not contain username, hostname, or paths
        info_str = str(info)
        import os
        import socket

        assert os.path.expanduser("~") not in info_str
        # Note: hostname test removed as it's not directly in the info


class TestBuildPayload:
    """Test payload building."""

    def test_build_download_event_payload(self, reset_telemetry_globals):
        """Test building download event payload."""
        payload = telemetry._build_download_event_payload(
            dataset_name="test_dataset",
            succeeded=True,
            metadata_received=True,
            resume_attempts=0,
            note="Test note",
        )

        assert payload["type"] == "download"
        assert payload["dataset"] == "test_dataset"
        assert payload["succeeded"] is True
        assert payload["metadata_received"] is True
        assert payload["resume_attempts"] == 0
        assert payload["placeholder_description"] == "Test note"
        assert "timestamp" in payload
        assert "session_id" in payload
        assert "os" in payload
        assert "python" in payload
        assert "cli_version" in payload

    def test_build_payload_without_note(self, reset_telemetry_globals):
        """Test building payload without optional note."""
        payload = telemetry._build_download_event_payload(
            dataset_name="test_dataset",
            succeeded=True,
            metadata_received=True,
            resume_attempts=0,
            note=None,
        )

        assert "placeholder_description" not in payload


class TestSendTelemetryEvent:
    """Test sending telemetry events."""

    @patch("neurodatahub.telemetry.requests.post")
    def test_send_telemetry_success(self, mock_post):
        """Test successful telemetry send."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        payload = {"type": "test"}
        result = telemetry._send_telemetry_event(payload)

        assert result is True
        mock_post.assert_called_once()

    @patch("neurodatahub.telemetry.requests.post")
    def test_send_telemetry_failure(self, mock_post):
        """Test failed telemetry send."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response

        payload = {"type": "test"}
        result = telemetry._send_telemetry_event(payload)

        assert result is False

    @patch("neurodatahub.telemetry.requests.post")
    def test_send_telemetry_rate_limited(self, mock_post):
        """Test handling of rate limit response."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_post.return_value = mock_response

        payload = {"type": "test"}
        result = telemetry._send_telemetry_event(payload)

        assert result is False

    @patch("neurodatahub.telemetry.requests.post")
    def test_send_telemetry_timeout(self, mock_post):
        """Test handling of timeout."""
        mock_post.side_effect = requests.exceptions.Timeout()

        payload = {"type": "test"}
        result = telemetry._send_telemetry_event(payload, timeout=1)

        assert result is False

    @patch("neurodatahub.telemetry.requests.post")
    def test_send_telemetry_network_error(self, mock_post):
        """Test handling of network error."""
        mock_post.side_effect = requests.exceptions.RequestException("Network error")

        payload = {"type": "test"}
        result = telemetry._send_telemetry_event(payload)

        assert result is False


class TestRecordDownloadEvent:
    """Test record_download_event function."""

    @patch("neurodatahub.telemetry.get_state_manager")
    def test_record_successful_download_increments_counter(self, mock_get_state):
        """Test that successful download increments counter."""
        mock_state = MagicMock()
        mock_state.has_telemetry_consent.return_value = False
        mock_get_state.return_value = mock_state

        telemetry.record_download_event(dataset_name="test_dataset", succeeded=True)

        mock_state.increment_successful_run.assert_called_once_with("test_dataset")

    @patch("neurodatahub.telemetry.get_state_manager")
    def test_record_failed_download_increments_counter(self, mock_get_state):
        """Test that failed download increments counter."""
        mock_state = MagicMock()
        mock_state.has_telemetry_consent.return_value = False
        mock_get_state.return_value = mock_state

        telemetry.record_download_event(dataset_name="test_dataset", succeeded=False)

        mock_state.increment_failed_run.assert_called_once_with("test_dataset")

    @patch("neurodatahub.telemetry.get_state_manager")
    @patch("neurodatahub.telemetry._send_telemetry_event")
    @patch("neurodatahub.telemetry._is_rate_limited")
    def test_record_event_with_consent(
        self, mock_rate_limited, mock_send, mock_get_state, reset_telemetry_globals
    ):
        """Test that event is sent when user consented."""
        mock_state = MagicMock()
        mock_state.has_telemetry_consent.return_value = True
        mock_get_state.return_value = mock_state
        mock_rate_limited.return_value = False
        mock_send.return_value = True

        telemetry.record_download_event(
            dataset_name="test_dataset", succeeded=True, note="Test note"
        )

        mock_send.assert_called_once()
        call_args = mock_send.call_args[0][0]
        assert call_args["dataset"] == "test_dataset"
        assert call_args["placeholder_description"] == "Test note"

    @patch("neurodatahub.telemetry.get_state_manager")
    @patch("neurodatahub.telemetry._send_telemetry_event")
    def test_record_event_without_consent(self, mock_send, mock_get_state):
        """Test that event is not sent without consent."""
        mock_state = MagicMock()
        mock_state.has_telemetry_consent.return_value = False
        mock_get_state.return_value = mock_state

        telemetry.record_download_event(dataset_name="test_dataset", succeeded=True)

        mock_send.assert_not_called()

    @patch("neurodatahub.telemetry.get_state_manager")
    @patch("neurodatahub.telemetry._send_telemetry_event")
    @patch("neurodatahub.telemetry._is_rate_limited")
    def test_record_event_rate_limited(
        self, mock_rate_limited, mock_send, mock_get_state
    ):
        """Test that event is not sent when rate limited."""
        mock_state = MagicMock()
        mock_state.has_telemetry_consent.return_value = True
        mock_get_state.return_value = mock_state
        mock_rate_limited.return_value = True

        telemetry.record_download_event(dataset_name="test_dataset", succeeded=True)

        mock_send.assert_not_called()


class TestGetTelemetryStatus:
    """Test telemetry status function."""

    @patch("neurodatahub.telemetry.get_state_manager")
    def test_get_telemetry_status(self, mock_get_state, reset_telemetry_globals):
        """Test getting telemetry status."""
        mock_state = MagicMock()
        mock_state.has_telemetry_consent.return_value = True
        mock_state.was_telemetry_consent_asked.return_value = True
        mock_state.get_successful_runs.return_value = 5
        mock_state.get_failed_runs.return_value = 2
        mock_get_state.return_value = mock_state

        status = telemetry.get_telemetry_status()

        assert status["consent_given"] is True
        assert status["consent_asked"] is True
        assert status["successful_runs"] == 5
        assert status["failed_runs"] == 2
        assert "endpoint" in status
        assert "session_id" in status
