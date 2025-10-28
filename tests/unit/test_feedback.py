"""Unit tests for feedback module."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from neurodatahub import feedback
from neurodatahub.state import StateManager


@pytest.fixture
def mock_state_manager(tmp_path):
    """Create a mock state manager for testing."""
    state_file = tmp_path / "test_state.json"
    return StateManager(state_file=state_file)


class TestFeedbackScheduling:
    """Test feedback scheduling logic."""

    def test_should_prompt_at_scheduled_runs(self):
        """Test that feedback is prompted at scheduled run counts."""
        for run_count in feedback.FEEDBACK_SCHEDULE:
            assert feedback._should_prompt_feedback(run_count, 0, force=False)

    def test_should_not_prompt_between_scheduled_runs(self):
        """Test that feedback is not prompted between scheduled runs."""
        assert not feedback._should_prompt_feedback(2, 0, force=False)
        assert not feedback._should_prompt_feedback(5, 0, force=False)
        assert not feedback._should_prompt_feedback(15, 0, force=False)

    def test_should_prompt_every_50_after_50(self):
        """Test that feedback is prompted every 50 runs after 50th."""
        assert feedback._should_prompt_feedback(100, 50, force=False)
        assert feedback._should_prompt_feedback(150, 100, force=False)
        assert feedback._should_prompt_feedback(200, 150, force=False)

    def test_should_not_prompt_at_same_run_count(self):
        """Test that feedback is not prompted at same run count twice."""
        assert not feedback._should_prompt_feedback(100, 100, force=False)
        assert not feedback._should_prompt_feedback(50, 50, force=False)

    def test_force_always_prompts(self):
        """Test that force=True always prompts."""
        assert feedback._should_prompt_feedback(2, 0, force=True)
        assert feedback._should_prompt_feedback(99, 50, force=True)
        assert feedback._should_prompt_feedback(100, 100, force=True)


class TestGetFeedbackChoice:
    """Test feedback choice prompts."""

    @patch("neurodatahub.feedback.Prompt.ask")
    def test_get_feedback_bad(self, mock_prompt):
        """Test selecting 'Bad' feedback."""
        mock_prompt.return_value = "1"
        result = feedback._get_feedback_choice()
        assert result == "Bad"

    @patch("neurodatahub.feedback.Prompt.ask")
    def test_get_feedback_fine(self, mock_prompt):
        """Test selecting 'Fine' feedback."""
        mock_prompt.return_value = "2"
        result = feedback._get_feedback_choice()
        assert result == "Fine"

    @patch("neurodatahub.feedback.Prompt.ask")
    def test_get_feedback_good(self, mock_prompt):
        """Test selecting 'Good' feedback."""
        mock_prompt.return_value = "3"
        result = feedback._get_feedback_choice()
        assert result == "Good"

    @patch("neurodatahub.feedback.Prompt.ask")
    def test_get_feedback_custom(self, mock_prompt):
        """Test selecting custom feedback."""
        mock_prompt.side_effect = ["4", "This is my custom feedback"]
        result = feedback._get_feedback_choice()
        assert result == "This is my custom feedback"

    @patch("neurodatahub.feedback.Prompt.ask")
    def test_get_feedback_skip(self, mock_prompt):
        """Test skipping feedback."""
        mock_prompt.return_value = "5"
        result = feedback._get_feedback_choice()
        assert result is None

    @patch("neurodatahub.feedback.Prompt.ask")
    def test_get_feedback_keyboard_interrupt(self, mock_prompt):
        """Test handling keyboard interrupt."""
        mock_prompt.side_effect = KeyboardInterrupt()
        result = feedback._get_feedback_choice()
        assert result is None


class TestGetFeedbackConsent:
    """Test feedback consent prompts."""

    @patch("neurodatahub.feedback.Confirm.ask")
    def test_get_consent_yes(self, mock_confirm):
        """Test user consents to feedback."""
        mock_confirm.return_value = True
        result = feedback._get_feedback_consent()
        assert result is True

    @patch("neurodatahub.feedback.Confirm.ask")
    def test_get_consent_no(self, mock_confirm):
        """Test user does not consent to feedback."""
        mock_confirm.return_value = False
        result = feedback._get_feedback_consent()
        assert result is False

    @patch("neurodatahub.feedback.Confirm.ask")
    def test_get_consent_keyboard_interrupt(self, mock_confirm):
        """Test handling keyboard interrupt during consent."""
        mock_confirm.side_effect = KeyboardInterrupt()
        result = feedback._get_feedback_consent()
        assert result is False


class TestGetFeedbackLevel:
    """Test feedback level selection."""

    @patch("neurodatahub.feedback.Prompt.ask")
    def test_get_level_short(self, mock_prompt):
        """Test selecting short feedback."""
        mock_prompt.return_value = "1"
        result = feedback._get_feedback_level()
        assert result == "short"

    @patch("neurodatahub.feedback.Prompt.ask")
    def test_get_level_comprehensive(self, mock_prompt):
        """Test selecting comprehensive feedback."""
        mock_prompt.return_value = "2"
        result = feedback._get_feedback_level()
        assert result == "comprehensive"

    @patch("neurodatahub.feedback.Prompt.ask")
    def test_get_level_cancel(self, mock_prompt):
        """Test cancelling feedback level selection."""
        mock_prompt.return_value = "3"
        result = feedback._get_feedback_level()
        assert result is None


class TestGetComprehensiveFeedback:
    """Test comprehensive feedback collection."""

    @patch("builtins.input")
    @patch("neurodatahub.feedback.Confirm.ask")
    @patch("neurodatahub.feedback.Prompt.ask")
    def test_get_comprehensive_all_fields(self, mock_prompt, mock_confirm, mock_input):
        """Test collecting all comprehensive fields."""
        mock_prompt.side_effect = [
            "advanced",  # research experience
            "Test University",  # institution
            "Testing neurodatahub for research",  # project
            "https://github.com/test/repo",  # github link
        ]
        mock_confirm.return_value = False  # No agent help
        mock_input.return_value = ""  # No log input

        result = feedback._get_comprehensive_feedback()

        assert result["research_experience"] == "advanced"
        assert result["institution"] == "Test University"
        assert result["project_description"] == "Testing neurodatahub for research"
        assert result["github_link"] == "https://github.com/test/repo"

    @patch("builtins.input")
    @patch("neurodatahub.feedback.Confirm.ask")
    @patch("neurodatahub.feedback.Prompt.ask")
    def test_get_comprehensive_skip_fields(self, mock_prompt, mock_confirm, mock_input):
        """Test skipping optional fields."""
        mock_prompt.side_effect = [
            "skip",  # research experience
            "",  # institution (empty)
            "",  # project
            "",  # github link
        ]
        mock_confirm.return_value = False
        mock_input.return_value = ""

        result = feedback._get_comprehensive_feedback()

        assert "research_experience" not in result
        assert "institution" not in result
        assert "project_description" not in result
        assert "github_link" not in result

    @patch("builtins.input")
    @patch("neurodatahub.feedback.Confirm.ask")
    @patch("neurodatahub.feedback.Prompt.ask")
    def test_get_comprehensive_with_log_summary(
        self, mock_prompt, mock_confirm, mock_input
    ):
        """Test providing log summary."""
        mock_prompt.side_effect = [
            "skip",  # research experience
            "",  # institution
            "",  # project
            "",  # github link
        ]
        mock_confirm.return_value = False
        mock_input.side_effect = [
            '{"error_summary": "timeout", "resume_attempts_summary": 2}',
            "",  # End input
        ]

        result = feedback._get_comprehensive_feedback()

        assert "log_summary" in result
        assert result["log_summary"]["error_summary"] == "timeout"


class TestBuildFeedbackPayload:
    """Test feedback payload building."""

    def test_build_short_feedback_payload(self):
        """Test building short feedback payload."""
        payload = feedback._build_feedback_payload(
            feedback_text="Good", feedback_level="short"
        )

        assert payload["type"] == "feedback"
        assert payload["feedback_level"] == "short"
        assert payload["feedback_text"] == "Good"
        assert "timestamp" in payload
        assert "os" in payload
        assert "python" in payload
        assert "cli_version" in payload

    def test_build_comprehensive_feedback_payload(self):
        """Test building comprehensive feedback payload."""
        comprehensive_data = {
            "research_experience": "advanced",
            "institution": "Test University",
            "project_description": "Testing",
        }

        payload = feedback._build_feedback_payload(
            feedback_text="Custom feedback",
            feedback_level="comprehensive",
            comprehensive_data=comprehensive_data,
        )

        assert payload["feedback_level"] == "comprehensive"
        assert payload["feedback_text"] == "Custom feedback"
        assert payload["research_experience"] == "advanced"
        assert payload["institution"] == "Test University"
        assert payload["project_description"] == "Testing"


class TestSendFeedbackEvent:
    """Test sending feedback events."""

    @patch("neurodatahub.feedback.requests.post")
    def test_send_feedback_success(self, mock_post):
        """Test successful feedback send."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        payload = {"type": "feedback"}
        result = feedback._send_feedback_event(payload)

        assert result is True

    @patch("neurodatahub.feedback.requests.post")
    def test_send_feedback_failure(self, mock_post):
        """Test failed feedback send."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response

        payload = {"type": "feedback"}
        result = feedback._send_feedback_event(payload)

        assert result is False

    @patch("neurodatahub.feedback.requests.post")
    def test_send_feedback_timeout(self, mock_post):
        """Test handling timeout."""
        mock_post.side_effect = requests.exceptions.Timeout()

        payload = {"type": "feedback"}
        result = feedback._send_feedback_event(payload)

        assert result is False


class TestMaybePromptFeedback:
    """Test maybe_prompt_feedback function."""

    @patch("neurodatahub.feedback.get_state_manager")
    def test_no_prompt_when_not_scheduled(self, mock_get_state):
        """Test that feedback is not prompted when not scheduled."""
        mock_state = MagicMock()
        mock_state.get_successful_runs.return_value = 2
        mock_state.get_last_feedback_run_count.return_value = 0
        mock_get_state.return_value = mock_state

        with patch("neurodatahub.feedback._get_feedback_choice") as mock_choice:
            feedback.maybe_prompt_feedback(force=False)
            mock_choice.assert_not_called()

    @patch("neurodatahub.feedback.get_state_manager")
    @patch("neurodatahub.feedback._get_feedback_choice")
    def test_prompt_when_scheduled(self, mock_choice, mock_get_state):
        """Test that feedback is prompted when scheduled."""
        mock_state = MagicMock()
        mock_state.get_successful_runs.return_value = 1  # First run
        mock_state.get_last_feedback_run_count.return_value = 0
        mock_get_state.return_value = mock_state
        mock_choice.return_value = None  # User skips

        feedback.maybe_prompt_feedback(force=False)
        mock_choice.assert_called_once()

    @patch("neurodatahub.feedback.get_state_manager")
    @patch("neurodatahub.feedback._get_feedback_choice")
    @patch("neurodatahub.feedback._get_feedback_consent")
    @patch("neurodatahub.feedback._get_feedback_level")
    @patch("neurodatahub.feedback._send_feedback_event")
    def test_full_feedback_flow_short(
        self, mock_send, mock_level, mock_consent, mock_choice, mock_get_state
    ):
        """Test complete short feedback flow."""
        mock_state = MagicMock()
        mock_state.get_successful_runs.return_value = 1
        mock_state.get_last_feedback_run_count.return_value = 0
        mock_get_state.return_value = mock_state

        mock_choice.return_value = "Good"
        mock_consent.return_value = True
        mock_level.return_value = "short"
        mock_send.return_value = True

        feedback.maybe_prompt_feedback(force=False)

        mock_send.assert_called_once()
        mock_state.update_last_feedback_run_count.assert_called_once_with(1)

    @patch("neurodatahub.feedback.get_state_manager")
    @patch("neurodatahub.feedback._get_feedback_choice")
    @patch("neurodatahub.feedback._get_feedback_consent")
    def test_feedback_without_consent(self, mock_consent, mock_choice, mock_get_state):
        """Test that feedback is not sent without consent."""
        mock_state = MagicMock()
        mock_state.get_successful_runs.return_value = 1
        mock_state.get_last_feedback_run_count.return_value = 0
        mock_get_state.return_value = mock_state

        mock_choice.return_value = "Good"
        mock_consent.return_value = False

        with patch("neurodatahub.feedback._send_feedback_event") as mock_send:
            feedback.maybe_prompt_feedback(force=False)
            mock_send.assert_not_called()
            # But should still update last feedback count
            mock_state.update_last_feedback_run_count.assert_called_once_with(1)
