#!/bin/bash

MWL_DIR="/var/lib/pacs-local/worklists"
RETENTION_DAYS=2
LOG_FILE="/opt/orthanc/Scheduler/cleanup-orthanc-mwl/cleanup.log"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Cleanup started" >> "$LOG_FILE"

find "$MWL_DIR" \
    -type f \
    -name "*.wl" \
    -mtime +$RETENTION_DAYS \
    -print \
    -delete >> "$LOG_FILE" 2>&1

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Cleanup finished" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"
