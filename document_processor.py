import os
import re
from typing import Dict

from pdf2image import convert_from_path
from PIL import Image
import pytesseract

from database import save_document

TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
POPPLER_PATH = r"C:\Program Files\poppler-25.11.0\Library\bin"

pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD


# =========================
#  OCR HELPERS
# =========================

def pdf_to_image(pdf_path: str) -> str:
    """Convert first page of a PDF to a PNG image and return the image path."""
    pages = convert_from_path(pdf_path, 300, poppler_path=POPPLER_PATH)
    img_path = os.path.splitext(pdf_path)[0] + "_page1.png"
    pages[0].save(img_path, "PNG")
    return img_path


def extract_text(file_path: str) -> str:
    """Run OCR on an image or PDF and return extracted text."""
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        image_path = pdf_to_image(file_path)
    else:
        image_path = file_path

    img = Image.open(image_path)
    text = pytesseract.image_to_string(img)
    return text
print(extract_text)


# =========================
#  CLASSIFICATION
# =========================

def classify_document(text: str) -> str:
    t = text.lower()

    if "form w-2" in t or "w-2 wage and tax" in t or "wage and tax statement" in t:
        return "W2"

    if "pay stub" in t or "paystub" in t:
        return "Paystub"

    if "driver license" in t or "driver's license" in t or "driver licence" in t or "dln" in t:
        return "Driving License"

    if (
        "passport" in t
        or "united states of america" in t
        or "p<usa" in t
        or "p<" in t  
    ):
        return "Passport"

    if "flood hazard determination" in t or "standard flood hazard determination form" in t:
        return "Flood Certificate"

    return "Others"


# =========================
#  FIELD EXTRACTION
# =========================

# ---- PAYSTUB ----

def extract_fields_paystub(text: str) -> Dict:
    fields: Dict[str, str] = {}

    # Employer: first non-empty line after "EMPLOYER NAME/ADDRESS:"
    employer_match = re.search(
        r"EMPLOYER NAME/ADDRESS:\s*\n(.+)", text, re.IGNORECASE
    )
    if employer_match:
        fields["Employer_Name"] = employer_match.group(1).strip()

    # Employee: first non-empty line after "EMPLOYEE NAME/ADDRESS:"
    emp_match = re.search(
        r"EMPLOYEE NAME/ADDRESS:\s*\n(.+)", text, re.IGNORECASE
    )
    if emp_match:
        fields["Employee_Name"] = emp_match.group(1).strip()

    # Net Pay – look for 'NET PAY 4,198.46' style
    net_match = re.search(
        r"NET PAY\s*([\d,]+\.\d{2})", text, re.IGNORECASE
    )
    if net_match:
        fields["Net_Pay"] = net_match.group(1).strip()

    return fields


# ---- DRIVING LICENSE ----

def extract_fields_driving_license(text: str) -> Dict:
    fields: Dict[str, str] = {}

    # DL number – pattern like D089654796
    dl_match = re.search(r"\bDLN?\s*[:#]?\s*([A-Z0-9]{6,})", text, re.IGNORECASE)
    if not dl_match:
        dl_match = re.search(r"\b([A-Z]\d{6,})\b", text)
    if dl_match:
        fields["DL_number"] = dl_match.group(1).strip()

    # DOB – any MM/DD/YYYY, preferably near 'DOB'
    dob_match = re.search(
        r"DOB\s*[:#]?\s*(\d{2}/\d{2}/\d{4})", text, re.IGNORECASE
    )
    if not dob_match:
        dob_match = re.search(r"\b(\d{2}/\d{2}/\d{4})\b", text)
    if dob_match:
        fields["DOB"] = dob_match.group(1).strip()

    # Name – line in ALL CAPS with two words (e.g. SAMPLE JELANI)
    for line in text.splitlines():
        l = line.strip()
        if not l:
            continue
        if any(ch.isdigit() for ch in l):
            continue
        if l.upper() == l and len(l.split()) == 2:
            # avoid labels like "ARIZONA DRIVER" etc.
            low = l.lower()
            if not any(stop in low for stop in ["arizona", "driver", "license", "usa", "veteran"]):
                fields["Name"] = l.title()
                break

    return fields


# ---- W2 ----

def extract_fields_w2(text: str) -> Dict:
    fields: Dict[str, str] = {}

    # ---------- EIN ----------
    # Try to grab EIN near the "Employer identification number" label
    ein = None
    ein_block_match = re.search(
        r"Employer identification number.*?(?:\(EIN\))?(.*)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if ein_block_match:
        tail = ein_block_match.group(1)
        m2 = re.search(r"([0-9][0-9\-]{8,})", tail)
        if m2:
            ein = m2.group(1)

    # Fallback: first pattern like 78-8778788
    if not ein:
        m2 = re.search(r"\b\d{2}-\d{7}\b", text)
        if m2:
            ein = m2.group(0)

    if ein:
        fields["EIN"] = ein.strip()

    # ---------- YEAR ----------
    year = None

    # 1) Try normal '2022', '2023', etc.
    years_normal = re.findall(r"\b(20\d{2})\b", text)
    if years_normal:
        year = years_normal[-1]

    # 2) If still not found, handle OCR mistakes like '2O22' (O instead of 0)
    if not year:
        # match 2[0 or O][0-9 or O][0-9 or O]
        fuzzy_candidates = re.findall(r"\b2[0O][0-9O]{2}\b", text)
        if fuzzy_candidates:
            cand = fuzzy_candidates[-1]
            cand = cand.replace("O", "0")  # normalize O -> 0
            # simple sanity check
            if cand.startswith("20") and len(cand) == 4:
                year = cand

    if year:
        fields["Year"] = year

    # ---------- EMPLOYEE NAME ----------
    # Focus on region between the labels:
    region = text
    split1 = re.split(r"Employee's first name and initial", text, flags=re.IGNORECASE)
    if len(split1) > 1:
        region = split1[1]
        split2 = re.split(r"Employee's address and ZIP code", region, flags=re.IGNORECASE)
        if len(split2) > 0:
            region = split2[0]

    # In that region, pick first "Firstname Lastname" pattern
    name_match = re.search(r"\b([A-Z][a-z]+)\s+([A-Z][a-z]+)\b", region)
    if name_match:
        fields["Employee_Name"] = f"{name_match.group(1)} {name_match.group(2)}"

    return fields


# ---- PASSPORT ----

def extract_fields_passport(text: str) -> Dict:
    fields: Dict[str, str] = {}

    # COUNTRY
    if re.search(r"United States of America", text, re.IGNORECASE):
        fields["Country"] = "USA"

    mrz_line1 = None
    mrz_line2 = None
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    for i, ln in enumerate(lines):
        if ln.startswith("P<"):
            mrz_line1 = ln
            if i + 1 < len(lines):
                mrz_line2 = lines[i + 1]
            break

    # PASSPORT NUMBER
    passport_no = None
    if mrz_line2:
        m = re.search(r"([A-Z0-9]{8,10})", mrz_line2)
        if m:
            passport_no = m.group(1)

    if not passport_no:
        m = re.search(r"\b\d{8,10}\b", text)
        if m:
            passport_no = m.group(0)

    if passport_no:
        fields["Passport_number"] = passport_no

    # NAME
    if mrz_line1:
        try:
            country_code = mrz_line1[2:5]
            rest = mrz_line1[5:]
            surname, given_block = rest.split("<<", 1)
            given_name = given_block.replace("<", " ").strip()
            full_name = f"{given_name.title()} {surname.title()}"
            fields["Name"] = full_name
            if "Country" not in fields:
                fields["Country"] = country_code
        except Exception:
            pass

    if "Name" not in fields:
        for ln in lines:
            if ln.isupper() and 2 <= len(ln.split()) <= 3 and not any(ch.isdigit() for ch in ln):
                fields["Name"] = ln.title()
                break

    return fields
#print(extract_fields_passport)



# ---- FLOOD CERTIFICATE ----

def extract_fields_flood_certificate(text: str) -> Dict:
    fields: Dict[str, str] = {}

    # Borrower: "Borrower: KIRSHENBAUM, AHARON"
    borrower_match = re.search(
        r"Borrower:\s*([A-Z ,]+)", text, re.IGNORECASE
    )
    if borrower_match:
        fields["Borrower_name"] = borrower_match.group(1).strip().title()

    # Customer No / Customer Number
    cust_match = re.search(
        r"Customer\s+Number\s*([0-9]+)", text, re.IGNORECASE
    )
    if cust_match:
        fields["Customer_No"] = cust_match.group(1).strip()

    # Expire date: "Expires: 09-30-2023"
    exp_match = re.search(
        r"Expires:\s*([0-9/\-]+)", text, re.IGNORECASE
    )
    if exp_match:
        fields["Expire_date"] = exp_match.group(1).strip()

    return fields


def extract_key_fields(doc_type: str, text: str) -> Dict:
    if doc_type == "Paystub":
        return extract_fields_paystub(text)
    if doc_type == "Driving License":
        return extract_fields_driving_license(text)
    if doc_type == "W2":
        return extract_fields_w2(text)
    if doc_type == "Passport":
        return extract_fields_passport(text)
    if doc_type == "Flood Certificate":
        return extract_fields_flood_certificate(text)
    return {}


# =========================
#  MAIN ENTRY POINT
# =========================

def process_document(file_path: str) -> Dict:
    """End-to-end: OCR -> classify -> extract -> save to SQLite -> return result."""
    text = extract_text(file_path)
    doc_type = classify_document(text)
    key_fields = extract_key_fields(doc_type, text)

    file_name = os.path.basename(file_path)
    save_document(file_name=file_name, doc_type=doc_type, key_fields=key_fields)

    return {
        "file_name": file_name,
        "type_of_document": doc_type,
        "key_fields": key_fields,
    }


if __name__ == "__main__":
    # quick manual test (optional)
    test_path = os.path.join("uploads", "Doc4.pdf")
    print(process_document(test_path))
