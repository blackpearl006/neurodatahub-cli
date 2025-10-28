"""User feedback collection system for NeuroDataHub CLI.

This module implements a scheduled feedback prompt system that asks users for
feedback at specific run counts: 1, 3, 10, 30, 50, then every 50 thereafter.

Feedback is opt-in and follows the same privacy principles as telemetry:
- No PII collected unless explicitly provided by user (optional institution name)
- Clear consent notice before sending
- User chooses between short and comprehensive feedback
- Comprehensive feedback includes helper prompt for coding agents
"""

import json
import sys
from datetime import datetime
from typing import Dict, Optional

import requests
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from . import __version__
from .logging_config import get_logger
from .state import get_state_manager
from .telemetry import DEFAULT_TELEMETRY_ENDPOINT, _get_system_info

logger = get_logger(__name__)
console = Console()

# Feedback schedule: run counts when to prompt
FEEDBACK_SCHEDULE = [1, 3, 10, 30, 50]
FEEDBACK_INTERVAL_AFTER_50 = 50  # Every 50 runs after the 50th


def _should_prompt_feedback(
    current_runs: int, last_feedback_run: int, force: bool
) -> bool:
    """Determine if feedback should be prompted.

    Args:
        current_runs: Current successful run count
        last_feedback_run: Run count when feedback was last shown
        force: Force prompt regardless of schedule

    Returns:
        True if feedback should be prompted, False otherwise
    """
    if force:
        return True

    # Check if current run is in the schedule
    if current_runs in FEEDBACK_SCHEDULE:
        # Don't prompt twice at the same run count
        return current_runs != last_feedback_run

    # After 50th run, prompt every 50 runs
    if current_runs > 50 and current_runs % FEEDBACK_INTERVAL_AFTER_50 == 0:
        # Only prompt if we haven't shown feedback at this exact count
        return current_runs != last_feedback_run

    return False


def _get_feedback_choice() -> Optional[str]:
    """Prompt user for feedback selection.

    Returns:
        Feedback text (Bad/Fine/Good/custom message) or None if cancelled
    """
    console.print("\n[bold cyan]How are you feeling about NeuroDataHub?[/bold cyan]")
    console.print("[1] Bad")
    console.print("[2] Fine")
    console.print("[3] Good")
    console.print("[4] Custom message")
    console.print("[5] Skip")

    try:
        choice = Prompt.ask(
            "Your choice", choices=["1", "2", "3", "4", "5"], default="5"
        )

        if choice == "1":
            return "Bad"
        elif choice == "2":
            return "Fine"
        elif choice == "3":
            return "Good"
        elif choice == "4":
            message = Prompt.ask("Enter your feedback message (max 300 chars)").strip()
            return message[:300] if message else None
        else:
            return None

    except (KeyboardInterrupt, EOFError):
        console.print("\n[yellow]Feedback cancelled[/yellow]")
        return None


def _get_feedback_consent() -> bool:
    """Show consent notice and get user consent.

    Returns:
        True if user consents, False otherwise
    """
    consent_notice = """
[bold]We'd like to send this anonymous feedback to help us improve NeuroDataHub.[/bold]

This will include:
• Your feedback text
• OS platform, CLI version, Python version
• Minimal run-level data (success/failure counts)

[yellow]NO personal data collected:[/yellow]
• No file paths, usernames, emails, or hostnames
• No IP addresses are stored
    """

    console.print(
        Panel(consent_notice, title="Feedback Privacy Notice", border_style="cyan")
    )

    try:
        return Confirm.ask("Do you consent to send this feedback?", default=False)
    except (KeyboardInterrupt, EOFError):
        console.print("\n[yellow]Feedback cancelled[/yellow]")
        return False


def _get_feedback_level() -> Optional[str]:
    """Ask user to choose feedback level (short or comprehensive).

    Returns:
        "short", "comprehensive", or None if cancelled
    """
    console.print("\n[bold]Choose feedback level:[/bold]")
    console.print("[1] Short (recommended) - Just send your feedback")
    console.print("[2] Comprehensive - Include optional research context")
    console.print("[3] Cancel")

    try:
        choice = Prompt.ask("Your choice", choices=["1", "2", "3"], default="1")

        if choice == "1":
            return "short"
        elif choice == "2":
            return "comprehensive"
        else:
            return None

    except (KeyboardInterrupt, EOFError):
        console.print("\n[yellow]Feedback cancelled[/yellow]")
        return None


def _show_agent_helper_prompt() -> None:
    """Show helper prompt for coding agents to process logs."""
    helper_prompt = """
[bold cyan]Helper Prompt for Coding Agents[/bold cyan]

If you're using a coding agent to help craft comprehensive feedback,
copy the prompt below and paste it to your agent along with your CLI logs:

[yellow]═══════════════════════════════════════════════════════════════[/yellow]
[AGENT PROMPT]
I will provide CLI log lines from `neurodatahub-cli`. Please:
1) Remove all personal info, file paths, hostnames, and tokens.
2) Extract error types and counts, resume counts, and dataset metadata retrieval status.
3) Produce a short JSON summary with keys: {error_summary, resume_attempts_summary, metadata_received_summary, recommended_placeholder_text}.
4) Keep summary <500 words.
[END]
[yellow]═══════════════════════════════════════════════════════════════[/yellow]

After the agent generates the summary, paste it back here.
    """
    console.print(Panel(helper_prompt, border_style="yellow"))


def _get_comprehensive_feedback() -> Dict[str, str]:
    """Collect comprehensive feedback with optional fields.

    Returns:
        Dictionary with optional comprehensive feedback fields
    """
    console.print("\n[bold]Comprehensive Feedback (all fields optional)[/bold]")
    console.print("[dim]Press Enter to skip any field[/dim]\n")

    comprehensive = {}

    try:
        # Research experience level
        exp = Prompt.ask(
            "Research experience level",
            choices=["novice", "intermediate", "advanced", "skip"],
            default="skip",
        )
        if exp != "skip":
            comprehensive["research_experience"] = exp

        # Institution name
        institution = Prompt.ask("Institution name (optional)", default="").strip()
        if institution:
            comprehensive["institution"] = institution

        # Project description
        console.print(
            "\n[dim]High-level project description / why using NeuroDataHub:[/dim]"
        )
        project = Prompt.ask("Project description (optional)", default="").strip()
        if project:
            comprehensive["project_description"] = project[:500]

        # GitHub issue or repo
        github = Prompt.ask(
            "Link to GitHub issue or repo (optional)", default=""
        ).strip()
        if github:
            comprehensive["github_link"] = github

        # Log summary
        console.print(
            "\n[bold]Optional: Paste log snippet or agent-processed summary[/bold]"
        )
        console.print(
            "[yellow]WARNING: Remove secrets, tokens, and personal info![/yellow]"
        )

        if Confirm.ask(
            "Would you like help from a coding agent to process logs?", default=False
        ):
            _show_agent_helper_prompt()

        console.print(
            "\n[dim]Paste log summary as JSON or text (press Enter twice to finish):[/dim]"
        )
        log_lines = []
        try:
            while True:
                line = input()
                if not line:
                    break
                log_lines.append(line)
        except EOFError:
            pass

        if log_lines:
            log_text = "\n".join(log_lines).strip()
            # Try to parse as JSON first
            try:
                log_summary = json.loads(log_text)
                comprehensive["log_summary"] = log_summary
            except json.JSONDecodeError:
                # Store as plain text
                comprehensive["log_summary"] = {"text": log_text[:1000]}

    except (KeyboardInterrupt, EOFError):
        console.print(
            "\n[yellow]Comprehensive feedback cancelled, keeping collected data[/yellow]"
        )

    return comprehensive


def _build_feedback_payload(
    feedback_text: str, feedback_level: str, comprehensive_data: Optional[Dict] = None
) -> Dict:
    """Build feedback event payload.

    Args:
        feedback_text: User's feedback text
        feedback_level: "short" or "comprehensive"
        comprehensive_data: Optional comprehensive feedback data

    Returns:
        Feedback event payload
    """
    payload = {
        "type": "feedback",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "feedback_level": feedback_level,
        "feedback_text": feedback_text,
    }

    # Add system info
    payload.update(_get_system_info())

    # Add comprehensive data if provided
    if comprehensive_data:
        payload.update(comprehensive_data)

    return payload


def _send_feedback_event(
    payload: Dict, endpoint: Optional[str] = None, timeout: int = 5
) -> bool:
    """Send feedback event to backend.

    Args:
        payload: Feedback event payload
        endpoint: Optional custom endpoint URL
        timeout: Request timeout in seconds (default: 5)

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
            logger.debug("Feedback event sent successfully")
            return True
        else:
            logger.warning(f"Feedback send failed with status {response.status_code}")
            return False

    except requests.exceptions.Timeout:
        logger.warning("Feedback request timed out")
        return False
    except requests.exceptions.RequestException as e:
        logger.warning(f"Feedback request failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error sending feedback: {e}")
        return False


def maybe_prompt_feedback(force: bool = False, endpoint: Optional[str] = None) -> None:
    """Prompt user for feedback based on schedule or force flag.

    This function:
    1. Checks if feedback should be prompted based on run count
    2. Shows feedback selection prompt
    3. Gets user consent
    4. Collects feedback (short or comprehensive)
    5. Sends feedback to backend

    Args:
        force: Force prompt regardless of schedule
        endpoint: Optional custom feedback endpoint
    """
    state_manager = get_state_manager()

    # Get current run counts
    current_runs = state_manager.get_successful_runs()
    last_feedback_run = state_manager.get_last_feedback_run_count()

    # Check if we should prompt
    if not _should_prompt_feedback(current_runs, last_feedback_run, force):
        logger.debug(
            f"Not prompting feedback (runs={current_runs}, last={last_feedback_run})"
        )
        return

    # Get feedback choice
    feedback_text = _get_feedback_choice()
    if not feedback_text:
        console.print("[dim]Feedback skipped[/dim]")
        return

    # Get consent
    if not _get_feedback_consent():
        console.print("[yellow]Feedback not sent (consent not given)[/yellow]")
        # Still update the last feedback run count to avoid re-prompting
        state_manager.update_last_feedback_run_count(current_runs)
        return

    # Get feedback level
    feedback_level = _get_feedback_level()
    if not feedback_level:
        console.print("[yellow]Feedback cancelled[/yellow]")
        return

    # Collect comprehensive feedback if chosen
    comprehensive_data = None
    if feedback_level == "comprehensive":
        comprehensive_data = _get_comprehensive_feedback()

    # Build and send payload
    try:
        payload = _build_feedback_payload(
            feedback_text, feedback_level, comprehensive_data
        )

        console.print("\n[cyan]Sending feedback...[/cyan]")
        success = _send_feedback_event(payload, endpoint)

        if success:
            console.print("[green]✓ Feedback sent successfully! Thank you![/green]")
        else:
            console.print(
                "[yellow]⚠ Could not send feedback. Please try again later.[/yellow]"
            )

        # Update last feedback run count
        state_manager.update_last_feedback_run_count(current_runs)

    except Exception as e:
        logger.error(f"Error in feedback flow: {e}")
        console.print("[red]⚠ Error processing feedback[/red]")
