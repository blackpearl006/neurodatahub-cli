"""Unit tests for state management module."""

import json
import tempfile
from pathlib import Path

import pytest

from neurodatahub.state import StateManager, get_state_manager


@pytest.fixture(scope="function")
def temp_state_file(tmp_path):
    """Create a temporary state file for testing."""
    state_file = tmp_path / "test_state.json"
    # Ensure file doesn't exist before test
    if state_file.exists():
        state_file.unlink()
    yield state_file
    # Clean up after test
    if state_file.exists():
        state_file.unlink()


@pytest.fixture(scope="function")
def state_manager(temp_state_file):
    """Create a StateManager instance with temporary state file."""
    manager = StateManager(state_file=temp_state_file)
    yield manager
    # Ensure clean state after test
    if temp_state_file.exists():
        temp_state_file.unlink()


class TestStateManager:
    """Test StateManager functionality."""

    def test_default_state_structure(self, state_manager):
        """Test that default state has correct structure."""
        state = state_manager.load_state()

        assert "successful_runs" in state
        assert "failed_runs" in state
        assert "per_dataset" in state
        assert "last_feedback_run_count" in state
        assert "telemetry_consent_given" in state
        assert "telemetry_consent_asked" in state

        assert state["successful_runs"] == 0
        assert state["failed_runs"] == 0
        assert state["per_dataset"] == {}
        assert state["last_feedback_run_count"] == 0
        assert state["telemetry_consent_given"] is False
        assert state["telemetry_consent_asked"] is False

    def test_save_and_load_state(self, state_manager):
        """Test saving and loading state."""
        # Modify state
        state = state_manager.load_state()
        state["successful_runs"] = 5
        state["failed_runs"] = 2

        # Save and reload
        assert state_manager.save_state(state)
        reloaded_state = state_manager.load_state()

        assert reloaded_state["successful_runs"] == 5
        assert reloaded_state["failed_runs"] == 2

    def test_increment_successful_run(self, state_manager):
        """Test incrementing successful run counter."""
        state_manager.increment_successful_run()
        assert state_manager.get_successful_runs() == 1

        state_manager.increment_successful_run()
        assert state_manager.get_successful_runs() == 2

    def test_increment_successful_run_with_dataset(self, state_manager):
        """Test incrementing successful run counter with dataset tracking."""
        state_manager.increment_successful_run("dataset_a")

        assert state_manager.get_successful_runs() == 1

        dataset_stats = state_manager.get_dataset_stats("dataset_a")
        assert dataset_stats["success"] == 1
        assert dataset_stats["fail"] == 0

    def test_increment_failed_run(self, state_manager):
        """Test incrementing failed run counter."""
        state_manager.increment_failed_run()
        assert state_manager.get_failed_runs() == 1

        state_manager.increment_failed_run()
        assert state_manager.get_failed_runs() == 2

    def test_increment_failed_run_with_dataset(self, state_manager):
        """Test incrementing failed run counter with dataset tracking."""
        state_manager.increment_failed_run("dataset_b")

        assert state_manager.get_failed_runs() == 1

        dataset_stats = state_manager.get_dataset_stats("dataset_b")
        assert dataset_stats["success"] == 0
        assert dataset_stats["fail"] == 1

    def test_multiple_dataset_tracking(self, state_manager):
        """Test tracking multiple datasets."""
        state_manager.increment_successful_run("dataset_a")
        state_manager.increment_successful_run("dataset_a")
        state_manager.increment_failed_run("dataset_a")

        state_manager.increment_successful_run("dataset_b")
        state_manager.increment_failed_run("dataset_b")
        state_manager.increment_failed_run("dataset_b")

        stats_a = state_manager.get_dataset_stats("dataset_a")
        assert stats_a["success"] == 2
        assert stats_a["fail"] == 1

        stats_b = state_manager.get_dataset_stats("dataset_b")
        assert stats_b["success"] == 1
        assert stats_b["fail"] == 2

    def test_telemetry_consent_default(self, state_manager):
        """Test default telemetry consent status."""
        assert state_manager.has_telemetry_consent() is False
        assert state_manager.was_telemetry_consent_asked() is False

    def test_set_telemetry_consent_true(self, state_manager):
        """Test setting telemetry consent to True."""
        state_manager.set_telemetry_consent(True)

        assert state_manager.has_telemetry_consent() is True
        assert state_manager.was_telemetry_consent_asked() is True

    def test_set_telemetry_consent_false(self, state_manager):
        """Test setting telemetry consent to False."""
        state_manager.set_telemetry_consent(False)

        assert state_manager.has_telemetry_consent() is False
        assert state_manager.was_telemetry_consent_asked() is True

    def test_telemetry_consent_persistence(self, state_manager):
        """Test that telemetry consent persists across instances."""
        state_manager.set_telemetry_consent(True)

        # Create new instance with same file
        new_manager = StateManager(state_file=state_manager.state_file)
        assert new_manager.has_telemetry_consent() is True
        assert new_manager.was_telemetry_consent_asked() is True

    def test_feedback_run_count_tracking(self, state_manager):
        """Test feedback run count tracking."""
        assert state_manager.get_last_feedback_run_count() == 0

        state_manager.update_last_feedback_run_count(5)
        assert state_manager.get_last_feedback_run_count() == 5

        state_manager.update_last_feedback_run_count(10)
        assert state_manager.get_last_feedback_run_count() == 10

    def test_reset_state(self, state_manager):
        """Test resetting state to defaults."""
        # Modify state
        state_manager.increment_successful_run("dataset_x")
        state_manager.set_telemetry_consent(True)
        state_manager.update_last_feedback_run_count(10)

        # Reset
        state_manager.reset_state()

        # Verify defaults
        assert state_manager.get_successful_runs() == 0
        assert state_manager.get_failed_runs() == 0
        assert state_manager.has_telemetry_consent() is False
        assert state_manager.was_telemetry_consent_asked() is False
        assert state_manager.get_last_feedback_run_count() == 0

    def test_nonexistent_dataset_stats(self, state_manager):
        """Test getting stats for nonexistent dataset."""
        stats = state_manager.get_dataset_stats("nonexistent_dataset")
        assert stats["success"] == 0
        assert stats["fail"] == 0

    def test_state_file_creation(self, state_manager):
        """Test that state file is created on save."""
        assert not state_manager.state_file.exists()

        state_manager.increment_successful_run()

        assert state_manager.state_file.exists()

    def test_corrupted_state_file(self, temp_state_file):
        """Test handling of corrupted state file."""
        # Write invalid JSON
        temp_state_file.write_text("invalid json {{{")

        # Should load default state without error
        manager = StateManager(state_file=temp_state_file)
        state = manager.load_state()

        assert state["successful_runs"] == 0

    def test_empty_state_file(self, temp_state_file):
        """Test handling of empty state file."""
        temp_state_file.write_text("")

        manager = StateManager(state_file=temp_state_file)
        state = manager.load_state()

        assert state["successful_runs"] == 0

    def test_partial_state_file(self, temp_state_file):
        """Test that partial state is merged with defaults."""
        # Write partial state
        partial_state = {"successful_runs": 10}
        temp_state_file.write_text(json.dumps(partial_state))

        manager = StateManager(state_file=temp_state_file)
        state = manager.load_state()

        # Partial data preserved
        assert state["successful_runs"] == 10

        # Missing data filled with defaults
        assert "telemetry_consent_given" in state
        assert state["telemetry_consent_given"] is False


class TestGlobalStateManager:
    """Test global state manager singleton."""

    def test_get_state_manager_singleton(self):
        """Test that get_state_manager returns singleton."""
        manager1 = get_state_manager()
        manager2 = get_state_manager()

        assert manager1 is manager2
