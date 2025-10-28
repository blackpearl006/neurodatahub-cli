"""User feedback collection system for NeuroDataHub CLI (v2.0 - Reimagined).

This module implements a streamlined feedback system with:
- Implicit consent model (choosing a rating = consent)
- Privacy notice shown inline with rating choices (every 100 days)
- Rich interactive selections for research context
- Automatic log analysis with PII sanitization
- Single-page comprehensive feedback experience
"""

import json
from datetime import datetime
from typing import Dict, Optional

import requests
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

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


def _show_privacy_notice_if_needed() -> None:
    """Show privacy notice if it hasn't been shown in 100 days."""
    state_manager = get_state_manager()

    if state_manager.should_show_privacy_notice(days_threshold=100):
        privacy_notice = """
[bold cyan]NeuroDataHub Feedback Privacy Notice[/bold cyan]

We collect feedback to improve NeuroDataHub. This includes:
• Your feedback text and selections
• OS platform, CLI version, Python version
• Anonymized error summaries (PII removed)

[green]NOT collected:[/green]
• No file paths, usernames, emails, hostnames
• No IP addresses stored
• No persistent user identifiers

[dim]By providing feedback, you consent to send this information.
This notice will be shown again in 100 days.[/dim]
        """
        console.print(
            Panel(privacy_notice, title="Privacy Notice", border_style="cyan")
        )
        state_manager.mark_privacy_notice_shown()


def _get_feedback_rating() -> Optional[str]:
    """Prompt user for feedback rating with inline privacy notice.

    Returns:
        Rating text ("Bad", "Fine", "Good", custom message) or None if cancelled
    """
    # Show privacy notice if needed (every 100 days)
    _show_privacy_notice_if_needed()

    console.print("\n[bold cyan]How's your experience with NeuroDataHub?[/bold cyan]")
    console.print("[1] Bad - Having significant issues")
    console.print("[2] Fine - Works okay, some issues")
    console.print("[3] Good - Working well for my needs")
    console.print("[4] Excellent - Exceeding expectations!")
    console.print("[5] Custom message")
    console.print("[6] Cancel (skip feedback)")

    try:
        choice = Prompt.ask(
            "Your choice", choices=["1", "2", "3", "4", "5", "6"], default="6"
        )

        if choice == "1":
            return "Bad"
        elif choice == "2":
            return "Fine"
        elif choice == "3":
            return "Good"
        elif choice == "4":
            return "Excellent"
        elif choice == "5":
            message = Prompt.ask(
                "Enter your feedback message (max 300 chars)"
            ).strip()
            return message[:300] if message else None
        else:
            return None

    except (KeyboardInterrupt, EOFError):
        console.print("\n[yellow]Feedback cancelled[/yellow]")
        return None


def _get_feedback_detail_level() -> str:
    """Ask if user wants to provide detailed feedback.

    Returns:
        "quick" or "detailed" (never None - always send feedback)
    """
    console.print(
        "\n[bold]Would you like to add research context? (optional)[/bold]"
    )
    console.print("[1] No, send my rating now (recommended)")
    console.print("[2] Yes, I'll add details about my use case")

    try:
        choice = Prompt.ask("Your choice", choices=["1", "2"], default="1")

        if choice == "1":
            return "quick"
        else:
            return "detailed"

    except (KeyboardInterrupt, EOFError):
        console.print("\n[yellow]Sending quick feedback...[/yellow]")
        return "quick"


def _get_detailed_feedback_selections() -> Dict[str, str]:
    """Collect detailed feedback using rich selections.

    Returns:
        Dictionary with selected feedback fields
    """
    console.print(
        "\n[bold]Optional Research Context[/bold] [dim](all fields optional)[/dim]"
    )

    feedback_data = {}

    try:
        # Career stage
        console.print("\n[cyan]Academic/Career Stage:[/cyan]")
        console.print("[1] BSc/Undergraduate")
        console.print("[2] Masters")
        console.print("[3] PhD/Doctoral")
        console.print("[4] Postdoc")
        console.print("[5] Faculty/Professor")
        console.print("[6] Industry/Corporate")
        console.print("[7] Other")
        console.print("[8] Prefer not to say")

        stage = Prompt.ask(
            "Select stage",
            choices=["1", "2", "3", "4", "5", "6", "7", "8"],
            default="8",
        )
        stage_map = {
            "1": "BSc/Undergrad",
            "2": "Masters",
            "3": "PhD",
            "4": "Postdoc",
            "5": "Faculty",
            "6": "Industry",
            "7": "Other",
            "8": None,
        }
        if stage_map[stage]:
            feedback_data["career_stage"] = stage_map[stage]

        # Years of experience
        console.print("\n[cyan]Years of experience with neuroimaging:[/cyan]")
        console.print("[1] Less than 1 year")
        console.print("[2] 1-3 years")
        console.print("[3] 3-5 years")
        console.print("[4] 5+ years")
        console.print("[5] Skip")

        years = Prompt.ask("Select experience", choices=["1", "2", "3", "4", "5"], default="5")
        years_map = {
            "1": "<1 year",
            "2": "1-3 years",
            "3": "3-5 years",
            "4": "5+ years",
            "5": None,
        }
        if years_map[years]:
            feedback_data["experience_years"] = years_map[years]

        # Research area
        console.print("\n[cyan]Primary research area:[/cyan]")
        console.print("[1] Neuroscience")
        console.print("[2] Psychology/Cognitive Science")
        console.print("[3] Computer Science/AI/ML")
        console.print("[4] Medicine/Clinical Research")
        console.print("[5] Statistics/Methods")
        console.print("[6] Other")
        console.print("[7] Skip")

        area = Prompt.ask(
            "Select area", choices=["1", "2", "3", "4", "5", "6", "7"], default="7"
        )
        area_map = {
            "1": "Neuroscience",
            "2": "Psychology",
            "3": "CS/AI/ML",
            "4": "Medicine/Clinical",
            "5": "Statistics",
            "6": "Other",
            "7": None,
        }
        if area_map[area]:
            feedback_data["research_area"] = area_map[area]

        # Usage type
        console.print("\n[cyan]Primary use case:[/cyan]")
        console.print("[1] Course/Teaching")
        console.print("[2] Research Project")
        console.print("[3] Clinical Study")
        console.print("[4] Meta-Analysis")
        console.print("[5] Methods Development")
        console.print("[6] Other")
        console.print("[7] Skip")

        usage = Prompt.ask(
            "Select use case", choices=["1", "2", "3", "4", "5", "6", "7"], default="7"
        )
        usage_map = {
            "1": "Teaching",
            "2": "Research",
            "3": "Clinical",
            "4": "Meta-Analysis",
            "5": "Methods",
            "6": "Other",
            "7": None,
        }
        if usage_map[usage]:
            feedback_data["use_case"] = usage_map[usage]

        # Institution (optional text)
        console.print(
            "\n[cyan]Institution name (optional):[/cyan] [dim]Press Enter to skip[/dim]"
        )
        institution = Prompt.ask("Institution", default="").strip()
        if institution:
            feedback_data["institution"] = institution

        # GitHub link (optional text)
        console.print(
            "\n[cyan]GitHub issue or repo link (optional):[/cyan] [dim]Press Enter to skip[/dim]"
        )
        github = Prompt.ask("GitHub link", default="").strip()
        if github:
            feedback_data["github_link"] = github

    except (KeyboardInterrupt, EOFError):
        console.print(
            "\n[yellow]Skipping remaining fields, keeping collected data[/yellow]"
        )

    return feedback_data


def _show_optional_log_analysis_prompt(log_file_path: Optional[str]) -> None:
    """Show optional manual log analysis prompt after feedback is sent.

    Args:
        log_file_path: Path to download log file
    """
    if not log_file_path:
        return

    log_prompt = f"""
[bold cyan]Optional: Include Log Analysis (for power users)[/bold cyan]

If you'd like to include a structured summary of your run logs, copy the
following text and paste it into your coding assistant (ChatGPT, Claude, Gemini):

[yellow]───────────────────────────────────────────────────────────────[/yellow]
You are a log analysis agent. Read the log file located at:
[bold]{log_file_path}[/bold]

Summarize the log into JSON with the following fields:
{{
  "error_summary": "...",
  "resume_attempts_summary": "...",
  "metadata_received_summary": "...",
  "recommended_placeholder_text": "..."
}}

Keep it concise, anonymized, and do NOT include private paths or file content.
[yellow]───────────────────────────────────────────────────────────────[/yellow]

Once your coding assistant gives you the JSON summary, paste it below.
Press Enter twice when done (or just press Enter to skip):
    """
    console.print(Panel(log_prompt, border_style="cyan"))

    # Collect multi-line input
    log_lines = []
    try:
        console.print("[dim]Paste JSON summary (or press Enter to skip):[/dim]")
        while True:
            line = input()
            if not line:
                break
            log_lines.append(line)
    except (KeyboardInterrupt, EOFError):
        console.print("\n[dim]Skipping log analysis[/dim]")
        return None

    if not log_lines:
        console.print("[dim]No log analysis provided - that's okay![/dim]")
        return None

    # Try to parse JSON
    log_text = "\n".join(log_lines).strip()
    try:
        log_summary = json.loads(log_text)
        console.print("[green]✓ Log analysis received![/green]")
        return log_summary
    except json.JSONDecodeError:
        console.print(
            "[yellow]⚠ Could not parse JSON, storing as plain text[/yellow]"
        )
        return {"text": log_text[:1000]}


def _build_feedback_payload(
    rating: str,
    detail_level: str,
    detailed_data: Optional[Dict] = None,
    log_summary: Optional[Dict] = None,
) -> Dict:
    """Build feedback event payload.

    Args:
        rating: User's feedback rating
        detail_level: "quick" or "detailed"
        detailed_data: Optional detailed feedback selections
        log_summary: Optional log analysis summary

    Returns:
        Feedback event payload
    """
    payload = {
        "type": "feedback",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "feedback_level": detail_level,
        "feedback_rating": rating,
    }

    # Add system info
    payload.update(_get_system_info())

    # Add detailed data if provided
    if detailed_data:
        payload.update(detailed_data)

    # Add log summary if available
    if log_summary:
        # Only include summary, counts, and categories (not full excerpt for bandwidth)
        payload["log_analysis"] = {
            "summary": log_summary["summary"],
            "total_errors": log_summary["total_errors"],
            "total_warnings": log_summary["total_warnings"],
            "error_counts": log_summary["error_counts"],
        }

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
    2. Shows privacy notice inline with rating choices (every 100 days)
    3. Gets feedback rating (choosing a rating = implicit consent)
    4. Optionally collects detailed context with rich selections
    5. Automatically analyzes recent log file (if available)
    6. Sends feedback to backend

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

    # Get feedback rating (includes privacy notice if needed)
    rating = _get_feedback_rating()
    if not rating:
        console.print("[dim]Feedback cancelled[/dim]")
        # Still update last feedback run to avoid re-prompting immediately
        state_manager.update_last_feedback_run_count(current_runs)
        return

    # Implicit consent: user chose a rating, so they consent
    state_manager.set_feedback_consent(True)

    # Ask if they want to provide detailed feedback (always returns a value now)
    detail_level = _get_feedback_detail_level()

    # Collect detailed feedback if chosen
    detailed_data = None
    if detail_level == "detailed":
        detailed_data = _get_detailed_feedback_selections()

    # Build and send payload (WITHOUT log analysis initially)
    try:
        payload = _build_feedback_payload(
            rating, detail_level, detailed_data, log_summary=None
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

        # NOW show optional log analysis prompt (after feedback is sent)
        log_file_path = state_manager.get_current_download_log_path()
        if log_file_path and success:
            console.print(
                "\n[dim]Feedback sent! You can optionally add log analysis below.[/dim]"
            )
            log_summary = _show_optional_log_analysis_prompt(log_file_path)

            # If they provided log analysis, send it as a follow-up
            if log_summary:
                follow_up_payload = {
                    "type": "feedback_log_followup",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "original_rating": rating,
                    "log_analysis": log_summary,
                }
                follow_up_payload.update(_get_system_info())

                console.print("\n[cyan]Sending log analysis...[/cyan]")
                if _send_feedback_event(follow_up_payload, endpoint):
                    console.print("[green]✓ Log analysis sent![/green]")

    except Exception as e:
        logger.error(f"Error in feedback flow: {e}")
        console.print("[red]⚠ Error processing feedback[/red]")
