#!/bin/bash
API_URL="https://mrkoon-ocr-production.up.railway.app/extract"
echo "Testing User Image..."
response=$(curl -s -X POST "$API_URL" \
    -F "document_type=egyptian_tax_card" \
    -F "method=ai" \
    -F "file=@/Users/husseinsalah/.gemini/antigravity/brain/3f719a15-d578-4ce0-a4c4-e8f49a89b612/.user_uploaded/media_1788342852383.jpg")
echo "$response"
