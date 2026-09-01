import re

def parse_egyptian_tax_card(raw_text: str) -> dict:
    """
    Parses raw OCR text from an Egyptian Tax Card and extracts:
    - company_name
    - tax_registration_number
    """
    data = {
        "company_name": "",
        "tax_registration_number": ""
    }
    
    lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
    
    # 1. Extract tax_registration_number
    # Look for a 9-digit number, often formatted with dashes like 123-456-789
    # or just a 9 digit string
    for line in lines:
        # Match something like "123-456-789" or "123 456 789"
        tax_match = re.search(r'(\d{3})[\s\-]*(\d{3})[\s\-]*(\d{3})', line)
        if tax_match:
            data["tax_registration_number"] = f"{tax_match.group(1)}-{tax_match.group(2)}-{tax_match.group(3)}"
            break

    # 2. Extract company_name
    # Heuristic 1: Find explicit keys like "اسم الممول" or "اسم الشركة"
    for i, line in enumerate(lines):
        if "اسم الممول" in line or "اسم الشركة" in line or "السم" in line:
            parts = line.split(':')
            if len(parts) > 1 and len(parts[1].strip()) > 2:
                data["company_name"] = parts[1].strip()
            elif i + 1 < len(lines):
                data["company_name"] = lines[i+1].strip()
            break
            
    # Heuristic 2: For corporate tax cards, the name is usually directly under the tax office name.
    # We skip standard government headers and the first non-header line is usually the company name.
    if not data["company_name"]:
        ignore_keywords = ["جمهورية", "وزارة", "مصلحة", "مأمورية", "الشركات المساهمة", "ضرائب", "مسئولية محدود", "رقم", "بطاقة"]
        for line in lines:
            # Skip empty lines or lines that are just numbers/symbols
            if len(line) < 4 or not any(c.isalpha() for c in line):
                continue
                
            # Check if line is a known header
            is_header = any(keyword in line for keyword in ignore_keywords)
            if not is_header:
                # This is likely the company name (e.g. "كايزيك لتطوير الحلول التقنيه")
                data["company_name"] = line
                break
                 
    return data
