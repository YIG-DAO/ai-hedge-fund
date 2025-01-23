#!/bin/bash

# Load environment variables using Python
eval "$(python3 -c '
import os
from dotenv import load_dotenv
load_dotenv()
for key, value in os.environ.items():
    if value and " " not in value and ">" not in value and "<" not in value:
        print(f"export {key}=\"{value}\"")
')"

# Check for required environment variables
if [ -z "$PERPLEXITY_API_KEY" ]; then
    echo "Error: PERPLEXITY_API_KEY environment variable is not set"
    exit 1
fi

if [ -z "$POSTGRES_HOST" ] || [ -z "$POSTGRES_DB" ] || [ -z "$POSTGRES_USER" ] || [ -z "$POSTGRES_PASSWORD" ]; then
    echo "Error: Required PostgreSQL environment variables are not set"
    exit 1
fi

echo "Starting weekly reindustrialization report distribution..."

# Extract all tickers from fund.json and store them in an array
TICKERS=($(cat fund.json | jq -r '.holdings | .[] | .holdings[]'))

# Initialize empty fund state object
echo "{" > fund_state.json
echo "  \"holdings\": {" >> fund_state.json

# Counter for comma handling
COUNT=0
TOTAL=${#TICKERS[@]}
SUCCESSFUL_ANALYSES=0
FAILED_ANALYSES=0

# Process each ticker
for TICKER in "${TICKERS[@]}"
do
    echo "Processing $TICKER..."
    
    # Run analysis and capture output
    if ! RESULT=$(poetry run python src/main.py --ticker "$TICKER" --show-reasoning 2>&1); then
        echo "Error analyzing $TICKER: $RESULT"
        FAILED_ANALYSES=$((FAILED_ANALYSES + 1))
        continue
    fi
    
    # Extract the final result JSON block
    if ! FINAL_RESULT=$(echo "$RESULT" | awk '/Final Result:/{p=1;next} p{print}' | jq -c '.'); then
        echo "Error parsing result for $TICKER"
        FAILED_ANALYSES=$((FAILED_ANALYSES + 1))
        continue
    fi
    
    # Check if result is empty or null
    if [ -z "$FINAL_RESULT" ] || [ "$FINAL_RESULT" = "null" ]; then
        echo "No valid result for $TICKER"
        FAILED_ANALYSES=$((FAILED_ANALYSES + 1))
        continue
    fi
    
    # Add to fund state
    if [ $COUNT -gt 0 ]; then
        echo "," >> fund_state.json
    fi
    echo "    \"$TICKER\": $FINAL_RESULT" >> fund_state.json
    SUCCESSFUL_ANALYSES=$((SUCCESSFUL_ANALYSES + 1))
    COUNT=$((COUNT + 1))
done

# Close the JSON object
echo "  }" >> fund_state.json
echo "}" >> fund_state.json

echo "Analysis complete. Results written to fund_state.json"
echo "Successfully analyzed: $SUCCESSFUL_ANALYSES tickers"
echo "Failed analyses: $FAILED_ANALYSES tickers"

# Run the email distribution script
python3 -c "
from src.tools.db import get_subscriber_emails
from src.tools.report import send_email_report
import time

def distribute_reports():
    try:
        emails = get_subscriber_emails()
        total = len(emails)
        print(f'Starting distribution to {total} subscribers...')
        
        for i, email in enumerate(emails, 1):
            try:
                send_email_report([email])
                print(f'Sent report to {email} ({i}/{total})')
                time.sleep(1)  # Rate limiting
            except Exception as e:
                print(f'Failed to send to {email}: {e}')
        
        print('Distribution completed!')
    except Exception as e:
        print(f'Distribution error: {e}')

distribute_reports()
"

echo "Weekly report distribution completed!"
