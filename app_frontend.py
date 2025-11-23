import os

import streamlit as st
import pandas as pd

from database import init_db, fetch_all_documents
from document_processor import process_document

# Folder where files will be stored
UPLOAD_DIR = "uploads"


def ensure_upload_dir():
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR)


def main():
    # Basic page setup
    st.set_page_config(
        page_title="Document Classification & Key Field Extraction",
        layout="centered",
    )

    st.title("📄 Document Classification & Key Field Extraction")

    # Make sure DB and upload folder exist
    init_db()
    ensure_upload_dir()

    st.markdown("Upload a **Driving License, Passport, W2, Pay Stub, or Flood Certificate**.")
    st.markdown("The app will classify the document, extract key fields, and store them in SQLite.")

    # File uploader
    uploaded_file = st.file_uploader(
        "Upload a document (image or PDF)",
        type=["png", "jpg", "jpeg", "pdf"],
    )

    if uploaded_file is not None:
        # Save uploaded file to uploads/ folder
        saved_path = os.path.join(UPLOAD_DIR, uploaded_file.name)
        with open(saved_path, "wb") as f:
            f.write(uploaded_file.read())

        st.info(f"File saved as: `{saved_path}`")

        # Process the document (OCR + classify + extract + save to DB)
        with st.spinner("Processing document..."):
            result = process_document(saved_path)

        st.success("✅ Document processed and saved to database.")

        # Show result for this file
        st.subheader("Current Document Result")
        st.json(result)

    # Show all documents from DB
    st.subheader("📊 All Processed Documents (from SQLite)")

    rows = fetch_all_documents()
    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No documents processed yet. Upload a file to see results here.")

    st.caption("Backend: Python + Tesseract OCR + SQLite | Frontend: Streamlit")


if __name__ == "__main__":
    main()
