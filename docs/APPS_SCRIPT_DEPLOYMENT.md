# Google Apps Script Deployment Guide

This guide provides step-by-step instructions for deploying the NeuroDataHub telemetry backend using Google Apps Script.

## Prerequisites

- A Google account
- Access to Google Drive
- Access to Google Apps Script (https://script.google.com)

## Step 1: Create New Apps Script Project

1. Go to [Google Apps Script](https://script.google.com)
2. Click **"New project"** in the top-left
3. You'll see a new project with a default `Code.gs` file

## Step 2: Copy the Backend Code

1. Delete the default `function myFunction()` code in `Code.gs`
2. Open `apps_script/neurodatahub_backend.gs` from this repository
3. Copy all the code
4. Paste it into the `Code.gs` file in Google Apps Script editor
5. Rename the file (optional):
   - Click the filename "Code.gs" at the top
   - Rename to "neurodatahub_backend.gs"

## Step 3: Rename the Project

1. Click "Untitled project" at the top
2. Rename to "NeuroDataHub Telemetry Backend"
3. The project will save automatically

## Step 4: Test the Script (Optional)

Before deploying, you can test the script manually:

1. In the Apps Script editor, select the function `doPost` from the dropdown
2. Click the "Run" button (▶️)
3. If prompted, review and grant permissions:
   - Click "Review permissions"
   - Choose your Google account
   - Click "Advanced"
   - Click "Go to NeuroDataHub Telemetry Backend (unsafe)" (this is safe, it's your own script)
   - Click "Allow"
4. Check the "Execution log" at the bottom for any errors

Note: Running `doPost` directly won't work perfectly because it expects POST data, but it will verify that the script is authorized.

## Step 5: Deploy as Web App

1. Click the **"Deploy"** button in the top-right
2. Select **"New deployment"**
3. Click the gear icon (⚙️) next to "Select type"
4. Choose **"Web app"**
5. Configure the deployment:
   - **Description**: "NeuroDataHub Telemetry v1"
   - **Execute as**: **Me** (your Google account)
   - **Who has access**: **Anyone** (required for the CLI to send data)

   ⚠️ **Important**: Setting "Who has access" to "Anyone" means anyone with the URL can send telemetry data. This is necessary for the CLI to work, but ensure you keep the URL private (don't share it publicly).

6. Click **"Deploy"**
7. **Copy the "Web app URL"** - it will look like:
   ```
   https://script.google.com/macros/s/AKfycbwXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX/exec
   ```

   ⚠️ **Save this URL!** You'll need it in the next step.

## Step 6: Update the CLI with New URL (If Changed)

If you deployed your own Apps Script and got a new URL:

### Option A: Update the code directly (for maintainers)

1. Edit `neurodatahub/telemetry.py`
2. Update the `DEFAULT_TELEMETRY_ENDPOINT` constant:
   ```python
   DEFAULT_TELEMETRY_ENDPOINT = "YOUR_NEW_URL_HERE"
   ```
3. Edit `neurodatahub/feedback.py`
4. Import the updated endpoint or update if needed
5. Rebuild and republish the package

### Option B: Use environment variable override (for users)

Users can override the endpoint without code changes:

```bash
export NEURODATAHUB_TELEMETRY_ENDPOINT="YOUR_NEW_URL_HERE"
```

Or add to `~/.neurodatahub/config.yml`:
```yaml
telemetry:
  endpoint: "YOUR_NEW_URL_HERE"
```

## Step 7: Test the Deployment

Test the deployment using curl:

### Test POST (telemetry event)

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "type": "download",
    "timestamp": "2025-10-27T12:00:00Z",
    "dataset": "test_dataset",
    "succeeded": true,
    "metadata_received": true,
    "resume_attempts": 0,
    "os": "Linux",
    "python": "3.11.0",
    "cli_version": "1.0.0",
    "session_id": "test123"
  }' \
  "YOUR_WEB_APP_URL"
```

Expected response:
```json
{
  "status": "ok",
  "stored": true,
  "total_events": 1
}
```

### Test GET (read-only summary)

```bash
curl "YOUR_WEB_APP_URL"
```

Expected response:
```json
{
  "status": "ok",
  "counts": {
    "total_successful_runs": 1,
    "total_failed_runs": 0,
    "per_dataset": {
      "test_dataset": {"success": 1, "fail": 0}
    },
    "feedback_count": {"short": 0, "comprehensive": 0}
  },
  "total_events": 1,
  "last_updated": "2025-10-27T12:00:00.000Z"
}
```

## Step 8: Verify Data Storage in Google Drive

1. Go to [Google Drive](https://drive.google.com)
2. Look for a file named **`neurodatahub_telemetry.json`** in your root folder
3. Open the file to verify it contains the test event:
   ```json
   {
     "counts": {
       "total_successful_runs": 1,
       "total_failed_runs": 0,
       "per_dataset": {
         "test_dataset": {"success": 1, "fail": 0}
       },
       "feedback_count": {"short": 0, "comprehensive": 0}
     },
     "events": [
       {
         "type": "download",
         "timestamp": "2025-10-27T12:00:00Z",
         ...
       }
     ],
     "created_at": "2025-10-27T12:00:00.000Z",
     "last_updated": "2025-10-27T12:00:00.000Z"
   }
   ```

## Step 9: (Optional) Export to Google Sheets

The Apps Script includes an optional function to export data to a Google Sheet:

1. In the Apps Script editor, select function **`exportToSheet`** from the dropdown
2. Click the "Run" button (▶️)
3. Check the "Execution log" for the Sheet URL
4. Open the URL to view your telemetry data in a Sheet with two tabs:
   - **Events**: All individual telemetry/feedback events
   - **Summary**: Aggregated counts and statistics

You can run this function manually anytime to update the Sheet with latest data.

## Managing Your Deployment

### Updating the Script

If you need to update the backend code:

1. Edit the code in the Apps Script editor
2. Save your changes (Ctrl+S / Cmd+S)
3. Click **"Deploy"** → **"Manage deployments"**
4. Click the pencil icon (✏️) next to your active deployment
5. Change "Version" to "New version"
6. Add a description (e.g., "v2 - Added rate limiting")
7. Click **"Deploy"**

**Note**: The Web app URL will remain the same, so you don't need to update the CLI.

### Viewing Execution Logs

To debug issues or monitor usage:

1. In the Apps Script editor, click **"Executions"** in the left sidebar
2. You'll see all recent script executions with status and logs
3. Click on an execution to see detailed logs

### Setting Up Quotas and Monitoring

Google Apps Script has execution quotas. To monitor:

1. Go to **Resources** → **Cloud Platform project**
2. Click on the project link
3. Go to **IAM & Admin** → **Quotas**
4. Monitor Apps Script API usage

**Default quotas (free tier)**:
- URL Fetch calls: 20,000/day
- Script runtime: 6 min/execution
- Simultaneous executions: 30
- LockService wait time: 30 seconds

These should be sufficient for most use cases. If you need higher quotas, consider Google Cloud Platform billing.

## Security Considerations

### Data Privacy

- The script stores only anonymized data (no PII)
- Data is stored in your personal Google Drive
- Only you have access to the JSON file and Apps Script execution logs
- The Web app URL is the only authentication mechanism

### URL Security

- **Keep the Web app URL private** - don't share it publicly
- If the URL is compromised, you can redeploy with a new version
- Consider adding IP allowlisting if needed (requires Apps Script add-ons)

### Rate Limiting

The script includes built-in rate limiting:
- Max 100 events/minute (server-side)
- Returns 429 status if exceeded
- Client-side also limits to 10 events/minute

## Troubleshooting

### Issue: "Authorization required" error

**Solution**: Re-run the script from the editor and grant permissions (see Step 4).

### Issue: "Script function not found: doPost"

**Solution**: Make sure you copied the entire `neurodatahub_backend.gs` code, including the `doPost` function.

### Issue: "ReferenceError: DriveApp is not defined"

**Solution**: This should not happen. If it does, ensure you're using a standard Google account (not a restricted G Suite account).

### Issue: Data not appearing in Drive

**Solution**:
1. Check the "Executions" log for errors
2. Verify the script has permission to access Drive
3. Try running `loadTelemetryData()` manually from the editor

### Issue: "Service invoked too many times" error

**Solution**: You've hit Google Apps Script quotas. Wait 24 hours for quota reset, or upgrade to Cloud Platform billing.

## Backup and Data Export

### Manual Backup

1. Download `neurodatahub_telemetry.json` from Google Drive
2. Store in a safe location

### Automated Backup

Set up a Google Apps Script trigger to export to Sheets daily:

1. In the Apps Script editor, click **"Triggers"** (clock icon) in the left sidebar
2. Click **"Add Trigger"**
3. Configure:
   - Choose function: `exportToSheet`
   - Deployment: Head
   - Event source: Time-driven
   - Type of time based trigger: Day timer
   - Time of day: Choose your preferred time
4. Click **"Save"**

This will automatically export data to a Google Sheet daily.

## Support

If you encounter issues with deployment:

1. Check the [Apps Script documentation](https://developers.google.com/apps-script)
2. Open an issue on [GitHub](https://github.com/blackpearl006/neurodatahub-cli/issues)
3. Email: reachninadaithal@gmail.com

---

**Congratulations!** You've successfully deployed the NeuroDataHub telemetry backend. The system is now ready to collect anonymized usage data from the CLI.
