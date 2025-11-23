# DocIntel – Document Classification & Key Field Extraction

DocIntel is a Python-based tool that automatically:

1. Identifies the **type of an uploaded document** (Driving License, W2, Paystub, Passport, Flood Certificate, Others)
2. Uses OCR to **extract key fields** specific to that document type
3. **Stores the extracted data in SQLite** and shows it in a Streamlit UI 

## Features

- Supports **images & PDFs** (JPG, PNG, PDF)
- Uses **Tesseract OCR** to read text from documents
- **Rule-based classification** of document types (W2, Passport, Driving License, Paystub, Flood Certificate, Others) 

- Extracts required key fields:
  - **Driving License** – Name, DL number, DOB  
  - **Flood Certificate** – Borrower name, Customer No, Expire date  
  - **W2** – Employee Name, EIN, Year  
  - **Paystub** – Employee Name, Employer Name, Net Pay  
  - **Passport** – Name, Passport number, Country  

- Stores results in a **SQLite database** and displays them in a table with timestamp. 
- Simple **Streamlit web interface** – upload → process → view structured data 
