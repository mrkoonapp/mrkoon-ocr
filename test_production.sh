#!/bin/bash
API_URL="https://mrkoon-ocr-production.up.railway.app/extract"

printf "%-18s | %-6s | %-7s | %-30s | %-15s\n" "Image" "Method" "Time(s)" "Company Name" "Tax Number"
echo "------------------------------------------------------------------------------------------"

for img in test_image*.*; do
    if [ ! -f "$img" ]; then continue; fi

    for method in "ai" "python"; do
        # Record start time
        start_time=$(date +%s.%N)
        
        response=$(curl -s -X POST "$API_URL" \
            -F "document_type=egyptian_tax_card" \
            -F "method=$method" \
            -F "file=@$img")
            
        # Record end time
        end_time=$(date +%s.%N)
        
        # Calculate duration using python since bc might not be available or clean
        duration=$(python3 -c "print(f'{float($end_time) - float($start_time):.2f}')")
            
        # parse with python3
        parsed=$(python3 -c "
import sys, json
try:
    data = json.loads(sys.argv[1])
    c = data.get('company_name', 'N/A')
    t = data.get('tax_registration_number', 'N/A')
    # truncate
    c = (c[:27] + '...') if len(c) > 30 else c
    t = (t[:12] + '...') if len(t) > 15 else t
    print(f'{c}|{t}')
except Exception:
    print('Error|N/A')
" "$response")
        
        company=$(echo "$parsed" | cut -d'|' -f1)
        tax=$(echo "$parsed" | cut -d'|' -f2)
        
        printf "%-18s | %-6s | %-7s | %-30s | %-15s\n" "$img" "$method" "${duration}s" "$company" "$tax"
    done
done
