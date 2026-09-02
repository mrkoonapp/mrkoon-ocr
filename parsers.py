import re
import logging

logger = logging.getLogger(__name__)

# ── Optional: Egyptian Tax Number validation via python-stdnum ──
try:
    from stdnum.eg import tn as _eg_tn
    _HAS_STDNUM = True
    logger.info("python-stdnum loaded — Egyptian TN checksum validation enabled")
except ImportError:
    _HAS_STDNUM = False
    logger.warning("python-stdnum not installed — tax number validation will be format-only")


# Eastern Arabic → Western digit translation table
_ARABIC_TO_WESTERN = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')

# Government header / location keywords to skip when looking for company name
_IGNORE_KEYWORDS = [
    # Official headers
    "جمهورية", "وزارة", "مصلحة", "مأمورية", "الشركات", "ضرائب", "بطاقة",
    "المالية", "المصرية", "العربية",
    # Common OCR misspellings of headers
    "جىهوربة", "رزارة", "مصدة", "مسوبة", "لمصربة", "العربة",
    # Card metadata keywords
    "رقم", "مسئولية", "مسؤولية", "مسؤلية", "مسولية", "محدودة", "مطوده", "مطودء", "محطوده", "الاستثمار", "كود", "النشاط",
    "بداية", "بدايه", "تاريخ", "الاعلان", "الإعلان",
    # Location / tax-office names (common ones)
    "مصر", "حلوان", "قليوب", "دار السلام", "الزاويه", "الخضراء",
    "منفلوط", "منفلو ط", "ثان", "اول", "أول",
    "مركز", "محافظة", "مدينة", "حى", "حي", "شارع", "قسم",
    "القاهرة", "الجيزة", "الاسكندرية", "بالقاهرة",
    # Legal form labels
    "تأيعةً", "المساهمة", "التضامنية", "فردية", "فرديه",
]


def _validate_tax_number(digits: str) -> bool:
    """
    Validate an Egyptian tax registration number.
    Uses python-stdnum checksum if available, otherwise format-only (9 digits).
    """
    clean = re.sub(r'\D', '', digits)
    if len(clean) != 9:
        return False

    if _HAS_STDNUM:
        try:
            _eg_tn.validate(clean)
            return True
        except Exception:
            # Checksum failed — might still be a valid format that stdnum
            # doesn't cover, so fall through to format-only.
            return False

    return True  # Format-only fallback


def _extract_tax_number(lines: list[str]) -> str:
    """
    Extract the 9-digit tax registration number (XXX-XXX-XXX).
    Searches bottom→up because the number sits near the card's bottom-right.
    """
    # Pass 1: look for explicit dashed format  XXX-XXX-XXX
    for line in reversed(lines):
        m = re.search(r'(\d{3})\s*[-–]\s*(\d{3})\s*[-–]\s*(\d{3})', line)
        if m:
            digits = m.group(1) + m.group(2) + m.group(3)
            if not digits.startswith("201") and not digits.startswith("202"):
                if _validate_tax_number(digits):
                    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

    # Pass 2: Extract all digits from the line and use a sliding 9-digit window
    # to find the first valid tax number, skipping dates (which often start with 202x)
    for line in reversed(lines):
        clean_digits = re.sub(r'\D', '', line)
        if len(clean_digits) >= 9:
            for i in range(len(clean_digits) - 8):
                candidate = clean_digits[i:i+9]
                # Avoid capturing dates like 2024, 2025 which coincidentally pass checksum
                if candidate.startswith("201") or candidate.startswith("202"):
                    continue
                if _validate_tax_number(candidate):
                    return f"{candidate[:3]}-{candidate[3:6]}-{candidate[6:]}"

    return ""


def _extract_company_name(lines: list[str]) -> str:
    """
    Extract the company / taxpayer name from the OCR lines.
    Strategy:
      1. Look for explicit label keywords (اسم الممول / اسم الشركة)
      2. Fallback: pick the first non-header, non-metadata line
    """
    # Strategy 1: explicit label
    for i, line in enumerate(lines):
        if any(kw in line for kw in ("اسم الممول", "اسم الشركة", "الممول", "اسم")):
            # Check if the name is on the same line after a colon / dash
            for sep in (":", "：", "-", "–"):
                if sep in line:
                    parts = line.split(sep, 1)
                    value = parts[1].strip()
                    if len(value) > 2:
                        return value

            # Otherwise take the next non-empty line
            for j in range(i + 1, min(i + 3, len(lines))):
                candidate = lines[j].strip()
                if len(candidate) > 2 and not _is_header_or_metadata(candidate):
                    return candidate
            break

    # Strategy 2: skip all headers/metadata, take the first real content line
    for line in lines:
        if len(line) < 4:
            continue
        if not any(c.isalpha() for c in line):
            continue
        if _is_header_or_metadata(line):
            continue
        # Skip lines that look like addresses (contain numbers + street words)
        if re.search(r'\d', line) and any(kw in line for kw in ("ش ", "شارع", "عمارة", "ط ", "برج")):
            continue
        return line

    return ""


def _is_header_or_metadata(line: str) -> bool:
    """Check if a line is a government header, location name, or metadata."""
    return any(kw in line for kw in _IGNORE_KEYWORDS)


def parse_egyptian_tax_card(raw_text: str) -> dict:
    """
    Parses raw OCR text from an Egyptian Tax Card and extracts:
    - company_name
    - tax_registration_number

    Works with text that may contain Eastern Arabic numerals (٠-٩).
    """
    # Normalise Eastern Arabic numerals → Western digits
    normalised = raw_text.translate(_ARABIC_TO_WESTERN)

    data = {
        "company_name": "",
        "tax_registration_number": "",
    }

    lines = [line.strip() for line in normalised.split('\n') if line.strip()]

    data["tax_registration_number"] = _extract_tax_number(lines)
    data["company_name"] = _extract_company_name(lines)

    logger.info(f"Parsed tax card → company={data['company_name']!r}, "
                f"tax_number={data['tax_registration_number']!r}")
    return data
