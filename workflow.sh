#!/bin/bash

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

# Close the JSON structure
echo "  }" >> fund_state.json
echo "}" >> fund_state.json

echo "Analysis complete. Results written to fund_state.json"
echo "Successfully analyzed: $SUCCESSFUL_ANALYSES tickers"
echo "Failed analyses: $FAILED_ANALYSES tickers"
