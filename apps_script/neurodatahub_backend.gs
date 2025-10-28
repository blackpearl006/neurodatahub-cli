/**
 * NeuroDataHub Telemetry & Feedback Backend
 *
 * This Google Apps Script handles telemetry and feedback events from neurodatahub-cli.
 * It maintains a persistent JSON file in Google Drive with aggregated counts and event history.
 *
 * Features:
 * - Persistent JSON storage in Google Drive
 * - Atomic updates with LockService (prevents concurrent write conflicts)
 * - Rate limiting (429 response if over quota)
 * - doPost: Accept and store telemetry/feedback events
 * - doGet: Return read-only summary of counts
 *
 * File stored: neurodatahub_telemetry.json in Drive root
 *
 * Author: NeuroDataHub Team
 * License: MIT
 */

// Configuration
const TELEMETRY_FILE_NAME = 'neurodatahub_telemetry.json';
const MAX_EVENTS_PER_MINUTE = 100;
const RATE_LIMIT_WINDOW = 60 * 1000; // 60 seconds in milliseconds

// Global rate limiting tracker (in-memory, resets when script restarts)
let recentEventTimestamps = [];

/**
 * Handle POST requests (telemetry and feedback events)
 */
function doPost(e) {
  try {
    // Check rate limit
    if (isRateLimited()) {
      return createJsonResponse(429, {
        status: 'error',
        reason: 'Rate limit exceeded. Please try again later.'
      });
    }

    // Parse incoming JSON
    let payload;
    try {
      payload = JSON.parse(e.postData.contents);
    } catch (parseError) {
      return createJsonResponse(400, {
        status: 'error',
        reason: 'Invalid JSON payload'
      });
    }

    // Validate payload
    const validTypes = ['download', 'feedback', 'feedback_log_followup'];
    if (!payload.type || !validTypes.includes(payload.type)) {
      return createJsonResponse(400, {
        status: 'error',
        reason: 'Invalid event type. Must be "download", "feedback", or "feedback_log_followup".'
      });
    }

    // Acquire lock to prevent concurrent modifications
    const lock = LockService.getScriptLock();
    try {
      // Wait up to 30 seconds for lock
      lock.waitLock(30000);
    } catch (lockError) {
      return createJsonResponse(503, {
        status: 'error',
        reason: 'Server busy. Could not acquire lock.'
      });
    }

    try {
      // Load existing telemetry data
      const data = loadTelemetryData();

      // Update data based on event type
      if (payload.type === 'download') {
        updateDownloadEvent(data, payload);
      } else if (payload.type === 'feedback' || payload.type === 'feedback_log_followup') {
        updateFeedbackEvent(data, payload);
      }

      // Append event to history
      data.events.push(payload);

      // Limit event history to last 10,000 events (prevent unbounded growth)
      if (data.events.length > 10000) {
        data.events = data.events.slice(-10000);
      }

      // Save updated data
      saveTelemetryData(data);

      // Record event timestamp for rate limiting
      recordEventTimestamp();

      return createJsonResponse(200, {
        status: 'ok',
        stored: true,
        total_events: data.events.length
      });

    } finally {
      // Always release lock
      lock.releaseLock();
    }

  } catch (error) {
    Logger.log('Error in doPost: ' + error.toString());
    return createJsonResponse(500, {
      status: 'error',
      reason: 'Internal server error: ' + error.toString()
    });
  }
}

/**
 * Handle GET requests (read-only summary of counts)
 */
function doGet(e) {
  try {
    const data = loadTelemetryData();

    // Return only aggregated counts, not individual events
    return createJsonResponse(200, {
      status: 'ok',
      counts: data.counts,
      total_events: data.events.length,
      last_updated: data.last_updated || 'N/A'
    });

  } catch (error) {
    Logger.log('Error in doGet: ' + error.toString());
    return createJsonResponse(500, {
      status: 'error',
      reason: 'Internal server error: ' + error.toString()
    });
  }
}

/**
 * Update data structure with download event
 */
function updateDownloadEvent(data, payload) {
  const dataset = payload.dataset || 'unknown';
  const succeeded = payload.succeeded === true;

  // Update total counts
  if (succeeded) {
    data.counts.total_successful_runs += 1;
  } else {
    data.counts.total_failed_runs += 1;
  }

  // Update per-dataset counts
  if (!data.counts.per_dataset[dataset]) {
    data.counts.per_dataset[dataset] = { success: 0, fail: 0 };
  }

  if (succeeded) {
    data.counts.per_dataset[dataset].success += 1;
  } else {
    data.counts.per_dataset[dataset].fail += 1;
  }

  // Update last_updated timestamp
  data.last_updated = new Date().toISOString();
}

/**
 * Update data structure with feedback event
 */
function updateFeedbackEvent(data, payload) {
  // Initialize feedback counts if not exists
  if (!data.counts.feedback_count) {
    data.counts.feedback_count = {
      quick: 0,
      detailed: 0,
      // Legacy compatibility
      short: 0,
      comprehensive: 0,
      // Rating breakdown
      by_rating: {},
      // Log followups
      with_logs: 0
    };
  }

  // Handle feedback_log_followup separately
  if (payload.type === 'feedback_log_followup') {
    data.counts.feedback_count.with_logs += 1;
  } else {
    // Handle regular feedback
    const level = payload.feedback_level || 'quick';

    // New format: quick/detailed
    if (level === 'quick') {
      data.counts.feedback_count.quick += 1;
    } else if (level === 'detailed') {
      data.counts.feedback_count.detailed += 1;
    }

    // Legacy format: short/comprehensive (for backwards compatibility)
    if (level === 'short') {
      data.counts.feedback_count.short += 1;
    } else if (level === 'comprehensive') {
      data.counts.feedback_count.comprehensive += 1;
    }

    // Track ratings
    const rating = payload.feedback_rating || 'unknown';
    if (!data.counts.feedback_count.by_rating[rating]) {
      data.counts.feedback_count.by_rating[rating] = 0;
    }
    data.counts.feedback_count.by_rating[rating] += 1;
  }

  // Update last_updated timestamp
  data.last_updated = new Date().toISOString();
}

/**
 * Load telemetry data from Google Drive
 * Creates new file with default structure if it doesn't exist
 */
function loadTelemetryData() {
  const files = DriveApp.getFilesByName(TELEMETRY_FILE_NAME);

  if (files.hasNext()) {
    // File exists, load and parse
    const file = files.next();
    const content = file.getBlob().getDataAsString();

    try {
      return JSON.parse(content);
    } catch (parseError) {
      Logger.log('Error parsing telemetry file, creating new one: ' + parseError.toString());
      return getDefaultTelemetryData();
    }
  } else {
    // File doesn't exist, return default structure
    return getDefaultTelemetryData();
  }
}

/**
 * Save telemetry data to Google Drive
 */
function saveTelemetryData(data) {
  const files = DriveApp.getFilesByName(TELEMETRY_FILE_NAME);
  const content = JSON.stringify(data, null, 2);

  if (files.hasNext()) {
    // Update existing file
    const file = files.next();
    file.setContent(content);
  } else {
    // Create new file
    DriveApp.createFile(TELEMETRY_FILE_NAME, content, MimeType.PLAIN_TEXT);
  }
}

/**
 * Get default telemetry data structure
 */
function getDefaultTelemetryData() {
  return {
    counts: {
      total_successful_runs: 0,
      total_failed_runs: 0,
      per_dataset: {},
      feedback_count: {
        quick: 0,
        detailed: 0,
        short: 0,  // Legacy
        comprehensive: 0,  // Legacy
        by_rating: {},
        with_logs: 0
      }
    },
    events: [],
    created_at: new Date().toISOString(),
    last_updated: new Date().toISOString()
  };
}

/**
 * Check if we're currently rate limited
 */
function isRateLimited() {
  const now = Date.now();

  // Remove timestamps outside the window
  recentEventTimestamps = recentEventTimestamps.filter(timestamp => {
    return (now - timestamp) < RATE_LIMIT_WINDOW;
  });

  // Check if we've exceeded the limit
  return recentEventTimestamps.length >= MAX_EVENTS_PER_MINUTE;
}

/**
 * Record event timestamp for rate limiting
 */
function recordEventTimestamp() {
  recentEventTimestamps.push(Date.now());
}

/**
 * Create JSON response with proper content type
 */
function createJsonResponse(statusCode, data) {
  const output = ContentService.createTextOutput(JSON.stringify(data));
  output.setMimeType(ContentService.MimeType.JSON);

  // Note: Apps Script doesn't support setting HTTP status codes directly
  // The status field in the response indicates success/error
  return output;
}

/**
 * Optional: Manually trigger data export to Google Sheets
 * Run this from the Apps Script editor to create/update a Sheet
 */
function exportToSheet() {
  const data = loadTelemetryData();

  // Check if sheet exists
  let spreadsheet;
  const files = DriveApp.getFilesByName('NeuroDataHub Telemetry');

  if (files.hasNext()) {
    spreadsheet = SpreadsheetApp.open(files.next());
  } else {
    spreadsheet = SpreadsheetApp.create('NeuroDataHub Telemetry');
  }

  // Events sheet
  const eventsSheet = spreadsheet.getSheetByName('Events') || spreadsheet.insertSheet('Events');
  eventsSheet.clear();

  // Headers
  const headers = [
    'Timestamp', 'Type', 'Dataset', 'Succeeded', 'Metadata Received',
    'Resume Attempts', 'Feedback Level', 'Feedback Rating', 'Career Stage',
    'Experience Years', 'Research Area', 'Use Case', 'Institution',
    'GitHub Link', 'Log Analysis Summary', 'OS', 'Python', 'CLI Version', 'Session ID'
  ];
  eventsSheet.appendRow(headers);

  // Data rows
  data.events.forEach(event => {
    const row = [
      event.timestamp || '',
      event.type || '',
      event.dataset || '',
      event.succeeded !== undefined ? event.succeeded.toString() : '',
      event.metadata_received !== undefined ? event.metadata_received.toString() : '',
      event.resume_attempts || '',
      event.feedback_level || '',
      event.feedback_rating || '',
      event.career_stage || '',
      event.experience_years || '',
      event.research_area || '',
      event.use_case || '',
      event.institution || '',
      event.github_link || '',
      event.log_analysis ? JSON.stringify(event.log_analysis.summary || event.log_analysis) : '',
      event.os || '',
      event.python || '',
      event.cli_version || '',
      event.session_id || ''
    ];
    eventsSheet.appendRow(row);
  });

  // Summary sheet
  const summarySheet = spreadsheet.getSheetByName('Summary') || spreadsheet.insertSheet('Summary');
  summarySheet.clear();

  summarySheet.appendRow(['Metric', 'Value']);
  summarySheet.appendRow(['Total Successful Runs', data.counts.total_successful_runs]);
  summarySheet.appendRow(['Total Failed Runs', data.counts.total_failed_runs]);
  summarySheet.appendRow(['Total Events', data.events.length]);
  summarySheet.appendRow(['Quick Feedback Count', data.counts.feedback_count.quick || 0]);
  summarySheet.appendRow(['Detailed Feedback Count', data.counts.feedback_count.detailed || 0]);
  summarySheet.appendRow(['Feedback with Logs', data.counts.feedback_count.with_logs || 0]);
  summarySheet.appendRow(['Short Feedback (Legacy)', data.counts.feedback_count.short || 0]);
  summarySheet.appendRow(['Comprehensive Feedback (Legacy)', data.counts.feedback_count.comprehensive || 0]);
  summarySheet.appendRow(['Last Updated', data.last_updated || 'N/A']);

  // Add rating breakdown
  if (data.counts.feedback_count.by_rating) {
    summarySheet.appendRow(['', '']);
    summarySheet.appendRow(['Rating Breakdown', '']);
    Object.keys(data.counts.feedback_count.by_rating).forEach(rating => {
      summarySheet.appendRow([rating, data.counts.feedback_count.by_rating[rating]]);
    });
  }

  Logger.log('Export to Sheet completed: ' + spreadsheet.getUrl());
  return spreadsheet.getUrl();
}
