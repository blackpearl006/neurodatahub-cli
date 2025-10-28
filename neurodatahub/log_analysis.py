"""Log analysis utilities for extracting and sanitizing error information.

This module provides functions to:
1. Read and parse log files from downloads
2. Extract error messages and categorize them
3. Sanitize PII (file paths, usernames, tokens, IP addresses)
4. Generate structured error summaries for feedback
"""

import re
from pathlib import Path
from typing import Dict, List

from .logging_config import get_logger

logger = get_logger(__name__)

# Patterns for PII sanitization
PII_PATTERNS = [
    # File paths (Unix and Windows)
    (re.compile(r"/home/[^/\s]+"), "[HOME]"),
    (re.compile(r"/Users/[^/\s]+"), "[HOME]"),
    (re.compile(r"C:\\Users\\[^\\s]+"), "[HOME]"),
    (re.compile(r"/tmp/[a-zA-Z0-9_-]+"), "[TMP]"),
    # IP addresses
    (re.compile(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b"), "[IP]"),
    # Email addresses
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"), "[EMAIL]"),
    # AWS keys and tokens (partial matches)
    (re.compile(r"AKIA[0-9A-Z]{16}"), "[AWS_KEY]"),
    (re.compile(r"aws_secret_access_key\s*=\s*[A-Za-z0-9/+=]{40}"), "[AWS_SECRET]"),
    # Generic tokens and passwords
    (re.compile(r"(token|password|key|secret)[\"']?\s*[:=]\s*[\"']?[A-Za-z0-9/+=_-]{8,}"), "[TOKEN]"),
    # Hostnames
    (re.compile(r"\b[a-zA-Z0-9-]+\.local\b"), "[HOSTNAME]"),
    # Session IDs and UUIDs
    (re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b"), "[SESSION_ID]"),
]

# Error patterns to extract
ERROR_PATTERNS = {
    "metadata_http_error": re.compile(r"Metadata download HTTP error.*HTTP (\d+)", re.IGNORECASE),
    "metadata_timeout": re.compile(r"Metadata download timeout", re.IGNORECASE),
    "metadata_failed": re.compile(r"Metadata download failed.*: ([A-Za-z]+Error)", re.IGNORECASE),
    "aws_error": re.compile(r"AWS.*failed with exit code (\d+)", re.IGNORECASE),
    "network_error": re.compile(r"(ConnectionError|TimeoutError|NetworkError)", re.IGNORECASE),
    "auth_error": re.compile(r"(Authentication failed|credentials not configured|authorization)", re.IGNORECASE),
    "disk_space": re.compile(r"(No space left|insufficient.*space)", re.IGNORECASE),
    "permission_error": re.compile(r"Permission denied", re.IGNORECASE),
}


def sanitize_text(text: str) -> str:
    """Sanitize text by removing PII.

    Args:
        text: Text to sanitize

    Returns:
        Sanitized text with PII replaced by placeholders
    """
    sanitized = text
    for pattern, replacement in PII_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    return sanitized


def extract_error_lines(log_file_path: str, max_lines: int = 500) -> List[str]:
    """Extract error and warning lines from a log file.

    Args:
        log_file_path: Path to log file
        max_lines: Maximum number of lines to read (default: 500)

    Returns:
        List of error/warning lines
    """
    error_lines = []

    try:
        log_path = Path(log_file_path)
        if not log_path.exists():
            logger.warning(f"Log file not found: {log_file_path}")
            return []

        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            for i, line in enumerate(f):
                if i >= max_lines:
                    break

                # Extract lines containing ERROR or WARNING
                if " ERROR " in line or " WARNING " in line:
                    error_lines.append(line.strip())

    except Exception as e:
        logger.error(f"Error reading log file {log_file_path}: {e}")

    return error_lines


def categorize_errors(error_lines: List[str]) -> Dict[str, List[str]]:
    """Categorize errors by type.

    Args:
        error_lines: List of error log lines

    Returns:
        Dictionary mapping error categories to lists of sanitized error messages
    """
    categorized = {
        "metadata_errors": [],
        "network_errors": [],
        "auth_errors": [],
        "disk_errors": [],
        "permission_errors": [],
        "aws_errors": [],
        "other_errors": [],
    }

    for line in error_lines:
        sanitized_line = sanitize_text(line)

        # Check each error pattern
        matched = False

        # Metadata errors
        if ERROR_PATTERNS["metadata_http_error"].search(line):
            categorized["metadata_errors"].append(sanitized_line)
            matched = True
        elif ERROR_PATTERNS["metadata_timeout"].search(line):
            categorized["metadata_errors"].append(sanitized_line)
            matched = True
        elif ERROR_PATTERNS["metadata_failed"].search(line):
            categorized["metadata_errors"].append(sanitized_line)
            matched = True

        # AWS errors
        if ERROR_PATTERNS["aws_error"].search(line):
            categorized["aws_errors"].append(sanitized_line)
            matched = True

        # Network errors
        if ERROR_PATTERNS["network_error"].search(line):
            categorized["network_errors"].append(sanitized_line)
            matched = True

        # Auth errors
        if ERROR_PATTERNS["auth_error"].search(line):
            categorized["auth_errors"].append(sanitized_line)
            matched = True

        # Disk errors
        if ERROR_PATTERNS["disk_space"].search(line):
            categorized["disk_errors"].append(sanitized_line)
            matched = True

        # Permission errors
        if ERROR_PATTERNS["permission_error"].search(line):
            categorized["permission_errors"].append(sanitized_line)
            matched = True

        # Other errors
        if not matched and " ERROR " in line:
            categorized["other_errors"].append(sanitized_line)

    return categorized


def generate_error_summary(
    log_file_path: str, max_lines: int = 500
) -> Dict[str, any]:
    """Generate a structured error summary from a log file.

    Args:
        log_file_path: Path to log file
        max_lines: Maximum number of lines to analyze (default: 500)

    Returns:
        Dictionary with error summary including:
        - total_errors: Total error count
        - total_warnings: Total warning count
        - error_categories: Dictionary of categorized errors
        - error_counts: Counter of error types
        - log_excerpt: Recent sanitized error lines (max 20)
    """
    try:
        # Extract error lines
        error_lines = extract_error_lines(log_file_path, max_lines)

        if not error_lines:
            return {
                "total_errors": 0,
                "total_warnings": 0,
                "error_categories": {},
                "error_counts": {},
                "log_excerpt": [],
                "summary": "No errors found in log file",
            }

        # Count errors vs warnings
        error_count = sum(1 for line in error_lines if " ERROR " in line)
        warning_count = sum(1 for line in error_lines if " WARNING " in line)

        # Categorize errors
        categorized = categorize_errors(error_lines)

        # Count by category
        error_counts = {
            category: len(errors)
            for category, errors in categorized.items()
            if errors
        }

        # Get recent error excerpt (last 20 errors, sanitized)
        recent_errors = error_lines[-20:] if len(error_lines) > 20 else error_lines
        sanitized_excerpt = [sanitize_text(line) for line in recent_errors]

        # Generate human-readable summary
        summary_parts = []
        if error_count > 0:
            summary_parts.append(f"{error_count} errors")
        if warning_count > 0:
            summary_parts.append(f"{warning_count} warnings")

        if error_counts:
            top_category = max(error_counts, key=error_counts.get)
            summary_parts.append(f"Most common: {top_category}")

        summary = ", ".join(summary_parts) if summary_parts else "No errors"

        return {
            "total_errors": error_count,
            "total_warnings": warning_count,
            "error_categories": {
                k: v for k, v in categorized.items() if v
            },  # Only include non-empty categories
            "error_counts": error_counts,
            "log_excerpt": sanitized_excerpt,
            "summary": summary,
        }

    except Exception as e:
        logger.error(f"Error generating error summary: {e}")
        return {
            "total_errors": 0,
            "total_warnings": 0,
            "error_categories": {},
            "error_counts": {},
            "log_excerpt": [],
            "summary": f"Error analyzing log file: {str(e)}",
        }


def format_error_summary_for_feedback(error_summary: Dict[str, any]) -> str:
    """Format error summary as human-readable text for feedback.

    Args:
        error_summary: Error summary from generate_error_summary()

    Returns:
        Formatted text summary
    """
    lines = []

    lines.append(f"**Error Summary**: {error_summary['summary']}")

    if error_summary["total_errors"] > 0 or error_summary["total_warnings"] > 0:
        lines.append(
            f"- Total: {error_summary['total_errors']} errors, {error_summary['total_warnings']} warnings"
        )

    if error_summary["error_counts"]:
        lines.append("\n**Error Breakdown**:")
        for category, count in sorted(
            error_summary["error_counts"].items(), key=lambda x: x[1], reverse=True
        ):
            lines.append(f"- {category.replace('_', ' ').title()}: {count}")

    if error_summary["log_excerpt"]:
        lines.append(f"\n**Recent Errors** (last {len(error_summary['log_excerpt'])}):")
        for line in error_summary["log_excerpt"][-10:]:  # Show last 10
            # Extract just the log message part (after timestamp and log level)
            parts = line.split(" - ", maxsplit=3)
            if len(parts) >= 4:
                message = parts[3]
            else:
                message = line
            lines.append(f"  {message}")

    return "\n".join(lines)
