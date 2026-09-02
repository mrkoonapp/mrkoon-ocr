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
    # The user noted it ALWAYS has the style 333-333-333 on the lower right
    # We will first look for the explicit dashed format
    for line in lines:
        # Look for explicit XXX-XXX-XXX (with optional spaces)
        tax_match_explicit = re.search(r'(\d{3})\s*-\s*(\d{3})\s*-\s*(\d{3})', line)
        if tax_match_explicit:
            data["tax_registration_number"] = f"{tax_match_explicit.group(1)}-{tax_match_explicit.group(2)}-{tax_match_explicit.group(3)}"
            break
            
    # If explicit dashes not found, look for exactly 9 digits on a line, 
    # or a sequence of 9 digits separated by spaces.
    if not data["tax_registration_number"]:
        for line in reversed(lines):  # User said it's on the lower line, so search from bottom up
            # Look for 9 digits isolated or with spaces
            tax_match_loose = re.search(r'(?<!\d)(\d{3})[\s]*(\d{3})[\s]*(\d{3})(?!\d)', line)
            if tax_match_loose:
                data["tax_registration_number"] = f"{tax_match_loose.group(1)}-{tax_match_loose.group(2)}-{tax_match_loose.group(3)}"
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
    if not data["company_name"]:
        # Added common OCR misspellings like 'جىهوربة', 'رزارة', 'مصدة', 'مسوبة', 'لمصربة', 'العربة'
        ignore_keywords = [
            "جمهورية", "وزارة", "مصلحة", "مأمورية", "الشركات", "ضرائب", "مسئولية", "رقم", "بطاقة",
            "جىهوربة", "رزارة", "مصدة", "مسوبة", "لمصربة", "العربة", "مصر"
        ]
        for line in lines:
            if len(line) < 4 or not any(c.isalpha() for c in line):
                continue
                
            is_header = any(keyword in line for keyword in ignore_keywords)
            if not is_header:
                data["company_name"] = line
                break
                 
    return data
