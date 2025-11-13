import os
import re
import sys
import subprocess

# === CONFIG ===
BASE_DIR = os.path.join(os.getcwd(), "generated_reports")  # Folder containing text files
report_sections_to_generate = [
    'purpose and objectives',
    'conclusions',
    'Background Information',
    'Inspection Observations',
    'Building Code Information',
    'Assessment',
    'recommendations for repairs',
    'references'
]

def clean_text_files():
    if not os.path.isdir(BASE_DIR):
        print(f"❌ Directory '{BASE_DIR}' does not exist.")
        return

    # Normalize section names to lowercase for matching
    normalized_sections = {section.lower(): section for section in report_sections_to_generate}

    for filename in os.listdir(BASE_DIR):
        file_path = os.path.join(BASE_DIR, filename)

        # Only process .txt files
        if os.path.isfile(file_path) and filename.lower().endswith(".txt"):
            section_name_raw = os.path.splitext(filename)[0]  # filename without extension
            section_name = section_name_raw.lower().strip()

            print(f"🔍 Processing: {filename}")

            # Try to find matching standard section name
            matched_section = None
            for standard_section in normalized_sections:
                if standard_section in section_name:
                    matched_section = standard_section
                    break

            if not matched_section:
                print(f"⚠️ No matching section heading found for {filename}, skipping heading removal.")
            
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # ✅ Remove ONLY '#', '*' and '---' or longer dash sequences
            cleaned_content = content.replace("*", "").replace("#", "")
            cleaned_content = re.sub(r"-{3,}", "", cleaned_content)  # Removes sequences of --- or ---- etc.

            # ✅ Remove ONLY the first heading VARIATION even with spaces before/after
            if matched_section:
                heading_pattern = re.compile(
                    rf"(?i)^\s*{re.escape(normalized_sections[matched_section])}\s*[:\-–—]*\s*$",
                    re.MULTILINE
                )
                cleaned_content, count = heading_pattern.subn("", cleaned_content, count=1)
                if count > 0:
                    print(f"✅ Removed heading variant (with space support): {normalized_sections[matched_section]}")
                else:
                    print(f"⚠️ No matching heading variant removed from {filename}")

            # ✅ Clean extra blank lines (collapse multiple empty lines into one)
            cleaned_content = re.sub(r'\n\s*\n+', '\n\n', cleaned_content)

            # ✅ Strip leading/trailing whitespace cleanly
            cleaned_content = cleaned_content.strip() + "\n"

            # ✅ Write back to SAME file
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(cleaned_content)

            print(f"💾 Saved updated file: {filename}\n")

if __name__ == "__main__":
    clean_text_files()
