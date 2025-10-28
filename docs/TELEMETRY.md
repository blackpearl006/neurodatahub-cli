# NeuroDataHub CLI - Telemetry & Feedback

## Overview

NeuroDataHub CLI includes an **opt-in** telemetry and feedback system designed to help us understand how the tool is used and improve the user experience. This document explains what data is collected, how it's used, and how to control your privacy settings.

## Privacy First

**We take your privacy seriously.** The telemetry system is designed with privacy as a top priority:

### What is NOT Collected

- ❌ **No IP addresses** (not stored by our backend)
- ❌ **No usernames or email addresses**
- ❌ **No local file paths**
- ❌ **No hostnames or computer names**
- ❌ **No persistent user identifiers** (session IDs are ephemeral and reset every CLI run)
- ❌ **No AWS credentials or authentication tokens**
- ❌ **No dataset contents or file data**

### What IS Collected

The telemetry system collects only anonymized, aggregated usage information:

#### Download Events
- **Dataset ID** (e.g., "HBN", "ADNI") - which datasets are being downloaded
- **Success/failure status** - whether the download completed successfully
- **Metadata received status** - whether dataset metadata was successfully retrieved
- **Resume attempt count** - how many times a download was resumed
- **Optional user note** - if you provide one via the `--note` flag

#### System Information
- **OS platform** (e.g., "Linux", "Darwin", "Windows")
- **Python version** (e.g., "3.11.2")
- **CLI version** (e.g., "1.0.3")
- **Ephemeral session ID** - a temporary identifier for the current CLI run (not persisted)

#### Feedback Events
When you choose to provide feedback:
- **Feedback sentiment** (Bad/Fine/Good or custom message)
- **Feedback level** (short or comprehensive)
- **Optional comprehensive fields** (only if you choose to provide them):
  - Research experience level (novice/intermediate/advanced)
  - Institution name
  - Project description
  - GitHub issue/repo links
  - Anonymized log summaries

### Data Storage and Retention

- **Local storage**: Run counts and consent status are stored locally in `~/.neurodatahub/state.json`
- **Backend storage**: Anonymized events are sent to a secure Google Apps Script endpoint
- **Persistent storage**: Data is stored in a private JSON file in Google Drive
- **Access**: Only NeuroDataHub maintainers have access to the aggregated data
- **Retention**: Data is retained indefinitely for research and product improvement purposes
- **No third-party sharing**: Your data is never sold or shared with third parties

## How It Works

### First Download Flow

1. You run your first successful download with `neurodatahub pull DATASET_ID /path`
2. After the download completes, you'll see a **telemetry consent prompt**:
   ```
   NeuroDataHub Telemetry

   We collect anonymized usage data to improve NeuroDataHub:
   • Dataset download success/failure counts
   • OS platform, CLI version, Python version

   NOT collected:
   • No personal information (usernames, emails, file paths, hostnames)
   • No IP addresses are stored
   • No persistent user identifiers

   Enable telemetry? [Y/n]:
   ```
3. Choose `Y` to enable or `n` to disable
4. Your choice is saved locally and will be remembered for all future runs

### Feedback Prompts

Feedback prompts appear automatically at specific milestones:
- **Run 1** - After your first successful download
- **Run 3** - After your third successful download
- **Run 10** - After your tenth successful download
- **Run 30** - After your thirtieth successful download
- **Run 50** - After your fiftieth successful download
- **Every 50 runs after 50** - e.g., runs 100, 150, 200, etc.

You can also trigger feedback manually:
```bash
neurodatahub feedback
# or
neurodatahub --feedback
```

### Feedback Flow

1. Choose your sentiment: Bad / Fine / Good / Custom message / Skip
2. If you provide feedback, you'll see a **consent notice** explaining what will be sent
3. Choose to consent (send feedback) or decline (feedback not sent)
4. Choose feedback level:
   - **Short** (recommended) - Just your feedback text and system info
   - **Comprehensive** - Includes optional research context fields

#### Comprehensive Feedback

If you choose comprehensive feedback, you can optionally provide:
- **Research experience level** - Are you a novice, intermediate, or advanced researcher?
- **Institution name** - Your university or research institution (optional)
- **Project description** - High-level description of your research project (optional)
- **GitHub links** - Links to related issues or repositories (optional)
- **Log summaries** - Anonymized CLI logs or error summaries (optional)

**⚠️ Warning**: When providing log summaries, please manually remove any:
- Secret tokens or API keys
- Email addresses
- Local file paths
- Any other personal information

For help sanitizing logs, use the provided coding agent helper prompt.

## Opting In or Out

### Initial Setup

When you run your first successful download, you'll be prompted for consent. Your choice is saved in `~/.neurodatahub/state.json`.

### Changing Your Mind

You can change your telemetry preference at any time by editing the state file:

```bash
# View current state
cat ~/.neurodatahub/state.json

# To disable telemetry (set to false)
# Edit ~/.neurodatahub/state.json and set:
{
  "telemetry_consent_given": false,
  "telemetry_consent_asked": true,
  ...
}

# To enable telemetry (set to true)
{
  "telemetry_consent_given": true,
  "telemetry_consent_asked": true,
  ...
}
```

Alternatively, delete the state file to be prompted again on next download:
```bash
rm ~/.neurodatahub/state.json
```

### Disabling Telemetry Completely

To completely disable telemetry without being asked:

1. Edit `~/.neurodatahub/state.json`:
   ```json
   {
     "telemetry_consent_given": false,
     "telemetry_consent_asked": true
   }
   ```

2. Or set an environment variable (overrides state file):
   ```bash
   export NEURODATAHUB_TELEMETRY_ENABLED=false
   ```

## How We Use This Data

The collected data helps us:

1. **Prioritize dataset maintenance** - Identify which datasets are most popular
2. **Improve error handling** - Understand common failure modes
3. **Optimize download performance** - Track resume attempts and success rates
4. **Guide feature development** - Learn what workflows are most common
5. **Understand our user base** - Learn about research contexts and use cases (from optional feedback)

All data is used solely for improving NeuroDataHub. We never sell or share your data with third parties.

## Rate Limiting

To protect our backend and prevent abuse:
- The CLI limits telemetry events to **10 events per minute** (client-side)
- The backend limits incoming events to **100 events per minute** (server-side)
- Exceeding these limits results in events being silently dropped (no error to you)

## Technical Details

### Local State File

Location: `~/.neurodatahub/state.json`

Structure:
```json
{
  "successful_runs": 0,
  "failed_runs": 0,
  "per_dataset": {
    "HBN": {"success": 5, "fail": 1},
    ...
  },
  "last_feedback_run_count": 0,
  "telemetry_consent_given": true,
  "telemetry_consent_asked": true
}
```

This file stores only local counters and consent status. It contains no personally identifiable information.

### Backend Endpoint

- **URL**: `https://script.google.com/macros/s/AKfycbwWUrd4Z6NeOcLEi3iibXzzD19eb_0N5uhbT0OPivvhIzzBEWPTAOZbGjL4IJNfIzPu_w/exec`
- **Method**: POST (for events), GET (for read-only summary)
- **Format**: JSON
- **Timeout**: 3 seconds (fire-and-forget)
- **Error handling**: All network errors are silent - telemetry never breaks the CLI

### Example Payloads

#### Download Event
```json
{
  "type": "download",
  "timestamp": "2025-10-27T12:34:56Z",
  "dataset": "HBN",
  "succeeded": true,
  "metadata_received": true,
  "resume_attempts": 0,
  "placeholder_description": "Testing download feature",
  "os": "Linux",
  "python": "3.11.2",
  "cli_version": "1.0.3",
  "session_id": "a1b2c3d4"
}
```

#### Feedback Event (Short)
```json
{
  "type": "feedback",
  "timestamp": "2025-10-27T12:40:00Z",
  "feedback_level": "short",
  "feedback_text": "Good",
  "os": "Linux",
  "python": "3.11.2",
  "cli_version": "1.0.3"
}
```

#### Feedback Event (Comprehensive)
```json
{
  "type": "feedback",
  "timestamp": "2025-10-27T12:40:00Z",
  "feedback_level": "comprehensive",
  "feedback_text": "Great tool, would love more datasets!",
  "research_experience": "advanced",
  "institution": "Test University",
  "project_description": "Using for neuroimaging meta-analysis",
  "log_summary": {"error_summary": "No errors", "resume_attempts_summary": 0},
  "os": "Linux",
  "python": "3.11.2",
  "cli_version": "1.0.3"
}
```

## Questions or Concerns?

If you have questions about telemetry, privacy, or how your data is used:

- **Open an issue**: [GitHub Issues](https://github.com/blackpearl006/neurodatahub-cli/issues)
- **Email**: reachninadaithal@gmail.com
- **Documentation**: https://blackpearl006.github.io/NeuroDataHub/

We're committed to transparency and will gladly answer any questions about our telemetry system.

## Summary

- ✅ **Opt-in only** - You choose whether to participate
- ✅ **Privacy-first** - No PII, no persistent identifiers, no IP addresses
- ✅ **Transparent** - Full documentation of what's collected and why
- ✅ **Anonymous** - No way to link data back to you
- ✅ **Beneficial** - Helps us improve NeuroDataHub for everyone
- ✅ **Safe** - Never breaks the CLI, all errors are silent
- ✅ **Changeable** - Opt out anytime by editing state file

Thank you for considering helping us improve NeuroDataHub!
