#!/bin/bash

# Peace System - Single Entry Point
# Starts all services: collector, event_pipeline, web API, and frontend

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Array to store PIDs of background processes
PIDS=""

# Cleanup function to kill all background processes
cleanup() {
    echo -e "${YELLOW}Shutting down services...${NC}"
    for pid in $PIDS; do
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true
            wait "$pid" 2>/dev/null || true
        fi
    done
    echo -e "${GREEN}All services stopped.${NC}"
    exit 0
}

# Set trap to run cleanup on SIGINT, SIGTERM, and EXIT
trap cleanup SIGINT SIGTERM EXIT

echo -e "${GREEN}Starting Peace System...${NC}\n"

# 1. Start collector
echo -e "${YELLOW}Starting collector...${NC}"
cd "$SCRIPT_DIR/collectors"
./collector &
LAST_PID=$!
PIDS="$PIDS $LAST_PID"
echo -e "${GREEN}✓ Collector started (PID: $LAST_PID)${NC}\n"

# 2. Start event_pipeline
echo -e "${YELLOW}Starting event_pipeline...${NC}"
cd "$SCRIPT_DIR"
python3 event_pipeline.py &
LAST_PID=$!
PIDS="$PIDS $LAST_PID"
echo -e "${GREEN}✓ Event Pipeline started (PID: $LAST_PID)${NC}\n"

# 3. Start web API
echo -e "${YELLOW}Starting web API...${NC}"
cd "$SCRIPT_DIR"
python -m web.api &
LAST_PID=$!
PIDS="$PIDS $LAST_PID"
echo -e "${GREEN}✓ Web API started (PID: $LAST_PID)${NC}\n"

# 4. Start frontend dev server
echo -e "${YELLOW}Starting frontend dev server...${NC}"
cd "$SCRIPT_DIR/frontend"
npm run dev &
LAST_PID=$!
PIDS="$PIDS $LAST_PID"
echo -e "${GREEN}✓ Frontend started (PID: $LAST_PID), on http://localhost:5173/ ${NC}\n"

echo -e "${GREEN}All services started successfully!${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}\n"

# Wait for all processes
for pid in $PIDS; do
    wait "$pid"
done

# run with: `chmod +x run.sh` -> `./run.sh`