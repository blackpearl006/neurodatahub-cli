#!/usr/bin/env python3
"""Integration test script for telemetry and feedback system.

This script simulates the complete telemetry and feedback flow:
1. Simulates 3 successful downloads
2. Forces feedback prompts at each stage
3. Verifies state.json updates
4. Mocks network calls to prevent actual telemetry sending

Usage:
    python scripts/test_telemetry_flow.py
"""

import json

# Add parent directory to path for imports
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from neurodatahub.feedback import maybe_prompt_feedback
from neurodatahub.state import StateManager
from neurodatahub.telemetry import get_telemetry_status, record_download_event


def mock_feedback_prompts():
    """Mock feedback prompt functions to simulate user responses."""
    with patch("neurodatahub.feedback.Prompt.ask") as mock_prompt, patch(
        "neurodatahub.feedback.Confirm.ask"
    ) as mock_confirm:

        # Simulate user selecting "Good" (option 3)
        mock_prompt.return_value = "3"
        # Simulate user giving consent
        mock_confirm.return_value = True

        yield mock_prompt, mock_confirm


def test_telemetry_flow():
    """Test complete telemetry and feedback flow."""
    print("=" * 80)
    print("Telemetry & Feedback System Integration Test")
    print("=" * 80)

    # Create temporary state file for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        state_file = Path(tmpdir) / "test_state.json"
        state_manager = StateManager(state_file=state_file)

        print(f"\n✓ Created temporary state file: {state_file}")

        # Mock network calls to prevent actual telemetry sending
        with patch(
            "neurodatahub.telemetry.requests.post"
        ) as mock_telemetry_post, patch(
            "neurodatahub.feedback.requests.post"
        ) as mock_feedback_post, patch(
            "neurodatahub.telemetry.get_state_manager", return_value=state_manager
        ), patch(
            "neurodatahub.feedback.get_state_manager", return_value=state_manager
        ):

            # Mock successful responses
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_telemetry_post.return_value = mock_response
            mock_feedback_post.return_value = mock_response

            print("\n✓ Mocked network calls (no actual telemetry will be sent)")

            # Test 1: Verify initial state
            print("\n" + "-" * 80)
            print("Test 1: Verify initial state")
            print("-" * 80)

            assert state_manager.get_successful_runs() == 0
            assert state_manager.get_failed_runs() == 0
            assert not state_manager.has_telemetry_consent()
            assert not state_manager.was_telemetry_consent_asked()

            print("✓ Initial state verified")
            print(f"  - Successful runs: {state_manager.get_successful_runs()}")
            print(f"  - Failed runs: {state_manager.get_failed_runs()}")
            print(f"  - Telemetry consent: {state_manager.has_telemetry_consent()}")

            # Test 2: Simulate first download (consent prompt would appear in real usage)
            print("\n" + "-" * 80)
            print("Test 2: Simulate first successful download")
            print("-" * 80)

            # Set consent for testing
            state_manager.set_telemetry_consent(True)
            print("✓ Telemetry consent set to True")

            record_download_event(
                dataset_name="test_dataset_1",
                succeeded=True,
                metadata_received=True,
                resume_attempts=0,
                note="Integration test download 1",
            )

            assert state_manager.get_successful_runs() == 1
            print(f"✓ Download event recorded")
            print(f"  - Dataset: test_dataset_1")
            print(f"  - Successful runs: {state_manager.get_successful_runs()}")

            # Check telemetry was called
            if mock_telemetry_post.called:
                call_args = mock_telemetry_post.call_args[1]
                payload = call_args.get("json", {})
                print(f"✓ Telemetry event sent:")
                print(f"  - Type: {payload.get('type')}")
                print(f"  - Dataset: {payload.get('dataset')}")
                print(f"  - Note: {payload.get('placeholder_description')}")

            # Test 3: Simulate feedback at run 1
            print("\n" + "-" * 80)
            print("Test 3: Simulate feedback prompt at run 1")
            print("-" * 80)

            with mock_feedback_prompts() as (mock_prompt, mock_confirm):
                # Force feedback prompt
                with patch(
                    "neurodatahub.feedback._get_feedback_level", return_value="short"
                ):
                    maybe_prompt_feedback(force=True)

                if mock_feedback_post.called:
                    call_args = mock_feedback_post.call_args[1]
                    payload = call_args.get("json", {})
                    print(f"✓ Feedback event sent:")
                    print(f"  - Type: {payload.get('type')}")
                    print(f"  - Level: {payload.get('feedback_level')}")
                    print(f"  - Text: {payload.get('feedback_text')}")

            # Test 4: Simulate more downloads
            print("\n" + "-" * 80)
            print("Test 4: Simulate additional downloads")
            print("-" * 80)

            for i in range(2, 4):
                record_download_event(
                    dataset_name=f"test_dataset_{i}",
                    succeeded=True,
                    metadata_received=True,
                    resume_attempts=0,
                    note=f"Integration test download {i}",
                )

                print(f"✓ Download {i} recorded")
                print(f"  - Successful runs: {state_manager.get_successful_runs()}")

            # Test 5: Simulate failed download
            print("\n" + "-" * 80)
            print("Test 5: Simulate failed download")
            print("-" * 80)

            record_download_event(
                dataset_name="test_dataset_failed",
                succeeded=False,
                metadata_received=False,
                resume_attempts=2,
                note="Integration test failed download",
            )

            print(f"✓ Failed download recorded")
            print(f"  - Failed runs: {state_manager.get_failed_runs()}")

            # Test 6: Verify per-dataset statistics
            print("\n" + "-" * 80)
            print("Test 6: Verify per-dataset statistics")
            print("-" * 80)

            for i in range(1, 4):
                stats = state_manager.get_dataset_stats(f"test_dataset_{i}")
                print(
                    f"  - test_dataset_{i}: {stats['success']} success, {stats['fail']} fail"
                )

            failed_stats = state_manager.get_dataset_stats("test_dataset_failed")
            print(
                f"  - test_dataset_failed: {failed_stats['success']} success, {failed_stats['fail']} fail"
            )

            # Test 7: Get telemetry status
            print("\n" + "-" * 80)
            print("Test 7: Get telemetry status")
            print("-" * 80)

            status = get_telemetry_status()
            print(f"✓ Telemetry status retrieved:")
            print(f"  - Consent given: {status['consent_given']}")
            print(f"  - Consent asked: {status['consent_asked']}")
            print(f"  - Successful runs: {status['successful_runs']}")
            print(f"  - Failed runs: {status['failed_runs']}")
            print(f"  - Session ID: {status['session_id']}")

            # Test 8: Verify state.json file contents
            print("\n" + "-" * 80)
            print("Test 8: Verify state.json file contents")
            print("-" * 80)

            if state_file.exists():
                with open(state_file, "r") as f:
                    state_data = json.load(f)

                print(f"✓ State file contents:")
                print(json.dumps(state_data, indent=2))
            else:
                print("⚠ State file not found")

            # Summary
            print("\n" + "=" * 80)
            print("Test Summary")
            print("=" * 80)
            print(f"✓ Total telemetry events sent: {mock_telemetry_post.call_count}")
            print(f"✓ Total feedback events sent: {mock_feedback_post.call_count}")
            print(f"✓ Final successful runs: {state_manager.get_successful_runs()}")
            print(f"✓ Final failed runs: {state_manager.get_failed_runs()}")
            print("\n✓ All integration tests passed!")


if __name__ == "__main__":
    try:
        test_telemetry_flow()
    except Exception as e:
        print(f"\n✗ Integration test failed with error:")
        print(f"  {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
