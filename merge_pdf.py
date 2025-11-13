# merge_pdfs.py
import os
from PyPDF2 import PdfMerger

REFERENCES_DIR = os.path.join(os.getcwd(), "output_template")
FINAL_OUTPUT = os.path.join(REFERENCES_DIR, "final_report.pdf")
PDF_ORDER = [
    "front_temp.pdf",
    "llm_updated_output.pdf",
    "output_ref.pdf"
]

def merge_and_cleanup_pdfs():
    merger = PdfMerger()
    added_any = False

    for pdf_name in PDF_ORDER:
        pdf_path = os.path.join(REFERENCES_DIR, pdf_name)
        if os.path.exists(pdf_path):
            try:
                merger.append(pdf_path)
                added_any = True
                print(f"✅ Added: {pdf_name}")
            except Exception as e:
                print(f"⚠️ Failed to add {pdf_name}: {e}")
        else:
            print(f"⏩ Skipped (missing): {pdf_name}")

    if not added_any:
        print("⚠️ No PDFs to merge. Skipping final_report.pdf creation.")
        return False

    # Save final merged file
    merger.write(FINAL_OUTPUT)
    merger.close()
    print(f"🎉 Final merged PDF created: {FINAL_OUTPUT}")

    # Now cleanup original PDFs
    for pdf_name in PDF_ORDER:
        pdf_path = os.path.join(REFERENCES_DIR, pdf_name)
        if os.path.exists(pdf_path):
            try:
                os.remove(pdf_path)
                print(f"🧹 Deleted: {pdf_name}")
            except Exception as e:
                print(f"⚠️ Could not delete {pdf_name}: {e}")

    return True



merge_and_cleanup_pdfs()