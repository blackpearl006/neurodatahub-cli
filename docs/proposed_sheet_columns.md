# Proposed Google Sheet Schema for NeuroDataHub Telemetry

## Overview

This document proposes the schema for exporting telemetry and feedback data to Google Sheets. The Apps Script backend (`apps_script/neurodatahub_backend.gs`) includes an optional `exportToSheet()` function that creates a Google Sheet with this structure.

**Important**: The primary storage mechanism is the JSON file (`neurodatahub_telemetry.json`) in Google Drive. Google Sheets integration is **optional** and provided for easier data analysis and visualization.

## Sheet Structure

The exported workbook contains **two sheets**:

### 1. Events Sheet

Contains all individual telemetry and feedback events.

#### Columns

| Column Name | Data Type | Description | Source Field | Example |
|------------|-----------|-------------|--------------|---------|
| **Timestamp** | DateTime (ISO 8601) | When the event occurred (UTC) | `event.timestamp` | `2025-10-27T12:34:56Z` |
| **Type** | String | Event type | `event.type` | `download`, `feedback` |
| **Dataset** | String | Dataset identifier (download events only) | `event.dataset` | `HBN`, `ADNI`, `HCP` |
| **Succeeded** | Boolean | Whether download succeeded (download events only) | `event.succeeded` | `TRUE`, `FALSE` |
| **Metadata Received** | Boolean | Whether metadata was retrieved (download events only) | `event.metadata_received` | `TRUE`, `FALSE` |
| **Resume Attempts** | Integer | Number of resume attempts (download events only) | `event.resume_attempts` | `0`, `1`, `2` |
| **Feedback Level** | String | Feedback detail level (feedback events only) | `event.feedback_level` | `short`, `comprehensive` |
| **Feedback Text** | String | User's feedback message (feedback events only) | `event.feedback_text` | `Good`, `Bad`, `Custom message...` |
| **Research Experience** | String | User's research level (comprehensive feedback only) | `event.research_experience` | `novice`, `intermediate`, `advanced` |
| **Institution** | String | User's institution (comprehensive feedback only) | `event.institution` | `MIT`, `Stanford`, `IISc` |
| **OS** | String | Operating system | `event.os` | `Linux`, `Darwin`, `Windows` |
| **Python** | String | Python version | `event.python` | `3.11.2`, `3.9.7` |
| **CLI Version** | String | NeuroDataHub CLI version | `event.cli_version` | `1.0.3`, `1.1.0` |
| **Session ID** | String | Ephemeral session identifier | `event.session_id` | `a1b2c3d4`, `x9y8z7w6` |

#### Notes
- Empty cells indicate field not applicable for that event type
- Timestamp is in UTC (ISO 8601 format)
- Session ID is ephemeral and resets each CLI run (not a persistent user ID)

### 2. Summary Sheet

Contains aggregated counts and statistics.

#### Rows

| Metric | Value | Source | Description |
|--------|-------|--------|-------------|
| **Total Successful Runs** | Integer | `counts.total_successful_runs` | Total number of successful downloads |
| **Total Failed Runs** | Integer | `counts.total_failed_runs` | Total number of failed downloads |
| **Total Events** | Integer | `events.length` | Total number of events (downloads + feedback) |
| **Short Feedback Count** | Integer | `counts.feedback_count.short` | Number of short feedback submissions |
| **Comprehensive Feedback Count** | Integer | `counts.feedback_count.comprehensive` | Number of comprehensive feedback submissions |
| **Last Updated** | DateTime | `last_updated` | Timestamp of most recent update |

#### Additional Rows (if needed)
You can extend this sheet to include:
- Per-dataset success/failure counts (from `counts.per_dataset`)
- Average resume attempts per dataset
- Most popular datasets (by download count)
- Feedback sentiment distribution
- CLI version distribution

## JSON to Sheet Mapping

### Download Event Example

**JSON Payload:**
```json
{
  "type": "download",
  "timestamp": "2025-10-27T12:34:56Z",
  "dataset": "HBN",
  "succeeded": true,
  "metadata_received": true,
  "resume_attempts": 0,
  "placeholder_description": "Testing download",
  "os": "Linux",
  "python": "3.11.2",
  "cli_version": "1.0.3",
  "session_id": "a1b2c3d4"
}
```

**Sheet Row:**
| Timestamp | Type | Dataset | Succeeded | Metadata Received | Resume Attempts | Feedback Level | Feedback Text | Research Experience | Institution | OS | Python | CLI Version | Session ID |
|-----------|------|---------|-----------|-------------------|-----------------|----------------|---------------|---------------------|-------------|-----|--------|-------------|------------|
| 2025-10-27T12:34:56Z | download | HBN | TRUE | TRUE | 0 | | | | | Linux | 3.11.2 | 1.0.3 | a1b2c3d4 |

### Feedback Event Example (Short)

**JSON Payload:**
```json
{
  "type": "feedback",
  "timestamp": "2025-10-27T12:40:00Z",
  "feedback_level": "short",
  "feedback_text": "Good",
  "os": "Darwin",
  "python": "3.9.7",
  "cli_version": "1.0.3"
}
```

**Sheet Row:**
| Timestamp | Type | Dataset | Succeeded | Metadata Received | Resume Attempts | Feedback Level | Feedback Text | Research Experience | Institution | OS | Python | CLI Version | Session ID |
|-----------|------|---------|-----------|-------------------|-----------------|----------------|---------------|---------------------|-------------|-----|--------|-------------|------------|
| 2025-10-27T12:40:00Z | feedback | | | | | short | Good | | | Darwin | 3.9.7 | 1.0.3 | |

### Feedback Event Example (Comprehensive)

**JSON Payload:**
```json
{
  "type": "feedback",
  "timestamp": "2025-10-27T12:45:00Z",
  "feedback_level": "comprehensive",
  "feedback_text": "Great tool, needs more datasets",
  "research_experience": "advanced",
  "institution": "Indian Institute of Science",
  "project_description": "Neuroimaging meta-analysis",
  "log_summary": {"error_summary": "No errors"},
  "os": "Linux",
  "python": "3.11.2",
  "cli_version": "1.0.3"
}
```

**Sheet Row:**
| Timestamp | Type | Dataset | Succeeded | Metadata Received | Resume Attempts | Feedback Level | Feedback Text | Research Experience | Institution | OS | Python | CLI Version | Session ID |
|-----------|------|---------|-----------|-------------------|-----------------|----------------|---------------|---------------------|-------------|-----|--------|-------------|------------|
| 2025-10-27T12:45:00Z | feedback | | | | | comprehensive | Great tool, needs more datasets | advanced | Indian Institute of Science | Linux | 3.11.2 | 1.0.3 | |

## Implementation Notes

### Current Implementation

The `exportToSheet()` function in `apps_script/neurodatahub_backend.gs` already implements this schema. To use it:

1. Deploy the Apps Script (see `APPS_SCRIPT_DEPLOYMENT.md`)
2. Run the `exportToSheet()` function manually from the editor
3. Or set up a daily trigger to export automatically

### Optional Additional Columns

You may want to add these columns based on your needs:

#### Additional Download Event Columns
- **Placeholder Description** (`event.placeholder_description`) - User-provided note via `--note` flag
- **Download Duration** (if tracked) - Time taken for download
- **File Size** (if tracked) - Size of downloaded data

#### Additional Feedback Event Columns
- **Project Description** (`event.project_description`) - High-level project description
- **GitHub Link** (`event.github_link`) - Link to related GitHub issue/repo
- **Log Summary** (`event.log_summary`) - Serialized JSON of log summary (or separate columns for each field)

#### Additional Metadata Columns
- **Event ID** - Auto-generated unique identifier for each row
- **Received At** - Timestamp when backend received the event (vs. when client sent it)
- **Client IP** - ⚠️ **NOT RECOMMENDED** for privacy reasons

### Data Analysis Recommendations

Once data is in Google Sheets, you can:

1. **Create pivot tables** to analyze:
   - Download success rates by dataset
   - Most popular datasets
   - Error patterns by OS/Python version
   - Feedback sentiment over time

2. **Create charts** to visualize:
   - Downloads over time (line chart)
   - Success vs. failure rates (pie chart)
   - Dataset popularity (bar chart)
   - CLI version adoption (stacked area chart)

3. **Use Google Data Studio** for dashboards:
   - Connect Data Studio to the Google Sheet
   - Create interactive dashboards
   - Share with team members

4. **Export to CSV** for external analysis:
   - Use pandas, R, or other analysis tools
   - Perform statistical analysis
   - Generate research reports

## Privacy Considerations

When working with the exported Sheet data:

- **DO NOT** add columns for personally identifiable information
- **DO NOT** share the Sheet publicly (keep it private to your Google account)
- **DO NOT** merge this data with external datasets that contain PII
- **DO** ensure the Sheet has appropriate access controls
- **DO** respect user privacy as outlined in `TELEMETRY.md`

## Changes and Versioning

If you modify the schema:

1. Update this document with the changes
2. Update the `exportToSheet()` function in `apps_script/neurodatahub_backend.gs`
3. Document the schema version in the Summary sheet
4. Consider adding a "Schema Version" column to track changes over time

## Approval Process

**Developer Confirmation Required:**

Before finalizing the Google Sheet integration:

1. **Review this proposed schema** - Does it meet your analysis needs?
2. **Suggest modifications** - Are there additional columns you need?
3. **Confirm privacy compliance** - Does this schema respect user privacy?
4. **Test the implementation** - Run `exportToSheet()` and verify the output

Once approved, the schema can be considered final for the initial release. Future versions can extend it as needed.

---

**Status**: ✅ Proposed schema ready for developer review

**Questions or suggestions?** Open an issue on GitHub or email reachninadaithal@gmail.com
