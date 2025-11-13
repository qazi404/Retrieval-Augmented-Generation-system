import json
from reportlab.pdfgen import canvas
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.lib.colors import black, gray
from reportlab.lib.utils import ImageReader
import os
import sys





REFERENCES_DIR = os.path.join(os.getcwd(), "references")
GENERATED_REPORT_PATH = os.path.join(os.getcwd(), "generated_reports")
CANNED_REPORT_PATH = os.path.join(os.getcwd(), "canned_reports")
OUTPUT_DIR = os.path.join(os.getcwd(), "output_template")



def build_canned_sections(canned_discussion, base_path="canned_reports"):
    if not canned_discussion or not canned_discussion.strip():
        print("⚠️ No canned discussions provided.")
        return []  # Continue PDF generation with no canned sections

    section_titles = [
        title.strip()
        for title in canned_discussion.split(",")
        if title.strip()
    ]

    sections = []
    for title in section_titles:
        filename = f"{title.lower()}.txt"
        file_path = os.path.join(base_path, filename)
        if os.path.exists(file_path):
            sections.append({
                "heading": title,
                "file_path": file_path
            })
        else:
            print(f"⚠️ Canned report file not found for: {title} -> {file_path}")
    print(f"Canned sections built: {sections}")
    return sections


# === Read input JSON from argv if passed ===
if len(sys.argv) > 1:
    try:
        input_data = json.loads(sys.argv[1])
    except Exception as e:
        print("Invalid input json", e)
        input_data = {}
else:
    input_data = {}

client_name = input_data.get("client_name", "")
insured_name = input_data.get("insured_name", "")
claim_number = input_data.get("claim_number", "")
x_canned_discussion = input_data.get("heading", "")
address = input_data.get("address", "")

# === CONFIG ===
input_json = os.path.join(REFERENCES_DIR, "page_2.json")
output_pdf = os.path.join(OUTPUT_DIR, "llm_updated_output.pdf")
output_folder = GENERATED_REPORT_PATH
ref_image = os.path.join(REFERENCES_DIR, "ref.png")
ref_align = os.path.join(REFERENCES_DIR, "align.png")
full_image = os.path.join(REFERENCES_DIR, "fullimg.png")


LEFT_MARGIN = 50
RIGHT_MARGIN = 50
BOTTOM_MARGIN = 60
PAGE_NUMBER_Y = 30

HEADER_FONT = "Helvetica-Bold"
HEADER_SIZE = 12

HEADING_FONT = "Helvetica-Bold"
HEADING_SIZE = 14

BODY_FONT = "Helvetica"
BODY_SIZE = 11
PARAGRAPH_SPACING_MULTIPLIER = 1.2

HEADING_SPACING = HEADING_SIZE * 1.2  # numeric value, used to move Y after heading
disclaimer_heading_drawn = False


# === Header replacements ===
header_replacements = {
    "Report for State Farm Insurance": f"Report for {client_name}",
    "Re. Inspection of Carlisle Residence": f"Re. Inspection of {insured_name} Residence",
    "42-89G4-23R": claim_number,
    "2238 Elderslie Drive, Germantown, Tennessee": address
}

# === Multi-section support with optional subheadings and optional images ===
sections = [
    {
        "heading": "Purpose and Objectives",
        "content": """Conclusion
In conclusion, the fire damage to the subject property is confined to specific areas, allowing for a feasible repair strategy. The foundation remains intact, and with appropriate remediation efforts, the structure can be restored to its original condition, ensuring continued occupancy and safety for the residents.
"""
    },
    {
        "heading": "Conclusions",
        "content": """### Conclusions

This damage assessment report, dated October 12, 2025, evaluates the fire damage sustained by the two-story wood-framed structure located at the subject property. The building, constructed in 1999, features a basement foundation, asphalt shingle roofing, and exterior walls composed of brick veneer and vinyl siding. The site is characterized by gently sloping lawns, and the property is currently owner-occupied.

The inspection revealed that the fire originated in the chimney due to a defect in the flue system, leading to localized damage primarily affecting the chimney chase and the adjacent roof framing. The affected components include the chimney chase, roof rafters, and sheathing, with a total damaged area of approximately 950 square feet. Notably, five roof joists were found to be broken as a result of the fire's impact. However, the foundation and floor joists remain unaffected, indicating that the integrity of the structural foundation has not been compromised.

Based on the severity assessment, the damage is classified as moderate. The localized nature of the fire damage does not extend to the foundation, and there is no indication of substantial damage as defined by the International Building Code (IBC) 2021 standards. The structural evaluation confirms that the damage is repairable, allowing for the restoration of the affected areas without the need for extensive reconstruction.

In summary, the fire damage is confined to the chimney and adjacent roof framing, with the foundation remaining intact and unaffected. The recommendations for remediation include the replacement of the damaged framing members and the reconstruction of the chimney using fire-rated materials to prevent future incidents.

In my professional opinion, the structure remains repairable and can be restored to its pre-damage condition with the recommended repairs. The findings of this report are supported by the guidelines set forth in the IBC 2021 and the NFPA 921 Guide for Fire Investigation, ensuring compliance with current safety standards.

This report is intended for the exclusive use of the client and should not be distributed without prior consent. Should you have any questions or require further assistance regarding this assessment, please do not hesitate to contact me.

**Joel D. Wehrman, P.E.**
Wehrman Investigative Engineering, LLC"""
    },
    {
        "heading": "Site Visit and Observations",
        "subsections": [
            {
                "heading": "Background Information",
                "content": "Historical or contextual information about the site, building, or inspection scope."
            },
            {
                "heading": "Inspection Observations",
                "content": "General notes and observations recorded during the site visit."
            }
        ]
    },
    {
        "heading": "Post-Inspection Research",
        # "subsections": [
        #     {
        #         "heading": "Building Code Information",
        #         "content": "Relevant building codes and standards applicable to the inspection findings."
        #     }
        # ]
    },
    {
        "heading": "Assessment",
        "content": "Analysis and evaluation of the observations in the context of building standards and best practices."
    },



    {
        "heading": "Recommendations for Repairs",
        "content": "Suggested actions and repairs based on the inspection and assessment."
    },
    {
        "heading": "References",
        "content": "Citations or sources used in the research and report preparation.",
        "image_path": ref_image
    },
    {
        "heading": "Client Communication & Closing Note",

        "content": """On behalf of Wehrman Investigative Engineering, LLC, I appreciate the opportunity to have been of service by providing this inspection and damage evaluation report. This electronic
        version of the report is a convenience copy and as such, an original signed and sealed copy
        is available to our client. Should you have any questions in regard to this report or if I can
        be of further assistance, please do not hesitate to contact me.""",
        "left_image_path":full_image,
        "image_path": ref_align

    },
    {
        "heading": "Disclaimer",
        "content": """Wehrman Investigative Engineering, LLC (WIE) inspected, investigated and
expressed its opinions concerning the property in this report under private contract with State
Farm Insurance. The report is for the exclusive use of State Farm Insurance. In entering the
contract to inspect and investigate the property, WIE and State Farm Insurance did not intend
to bestow any direct or incidental benefit on the property owner, any tenants of the property
owner, or anyone else associated with the property owner. WIE and its agents and employees
do not have and do disclaim any contractual relationship with, or duty or obligation to, any
party other than the addressee of this report and the principals for whom the addressee is
acting. The report represents our best judgement regarding the specific issues of interest, is
based on simple visual inspection techniques and has not entailed a detailed structural
review. Neither the inspection nor investigation offer any implied warranty of safe condition
of the structure, regardless of any opinions or repair recommendations in the report. State
Farm Insurance must interpret and assess the applicability of the opinions expressed in this
report to the purposes for which it contracted with WIE for the inspection, investigation and
preparation of the report. In no event will WIE be responsible for any direct, indirect or consequential damages proximately caused by reliance on the opinions expressed in the report."""
    }
]


# === DYNAMIC HEADINGS (use lowercase matching in loader) ===
DYNAMIC_HEADINGS = {
    'purpose and objectives',
    'conclusions',
    'background information',
    'inspection observations',
    'assessment',
    'recommendations for repairs',
    'references'
}


def load_section_content(base_path, heading):
    """
    Loads a .txt file from the given base_path if the filename
    (without extension) matches the section heading (case-insensitive).
    Returns None if not found.
    """
    if not os.path.exists(base_path):
        os.makedirs(base_path, exist_ok=True)
        return None

    normalized_heading = heading.lower().strip()
    for file_name in os.listdir(base_path):
        clean_name = os.path.splitext(file_name)[0].lower().strip()
        if normalized_heading in clean_name:
            with open(os.path.join(base_path, file_name), "r", encoding="utf-8") as f:
                return f.read().strip()
    return None


# === Populate sections with generated .txt contents if available ===
for section in sections:
    if section["heading"].lower() in DYNAMIC_HEADINGS:
        content = load_section_content(GENERATED_REPORT_PATH, section["heading"])
        if content:
            section["content"] = content
    elif "subsections" in section:
        for sub in section["subsections"]:
            if sub["heading"].lower() in DYNAMIC_HEADINGS:
                content = load_section_content(GENERATED_REPORT_PATH, sub["heading"])
                if content:
                    sub["content"] = content

# === Try to insert user canned sections if provided ===
try:
    user_new_sections = build_canned_sections(x_canned_discussion)
    if not user_new_sections:
        print("⚠️ No user canned sections to insert.")
    else:
        insert_index = next(
            (i for i, s in enumerate(sections) if s["heading"].lower() == "assessment"),
            len(sections)
        )

        for new_sec in reversed(user_new_sections):
            heading = new_sec["heading"]
            # first try to load from canned folder
            content = load_section_content(CANNED_REPORT_PATH, heading)
            if not content:
                content = new_sec.get("content", "").strip()
            if content:
                sections.insert(insert_index, {"heading": heading, "content": content})
        print(f"✅ Inserted {len(user_new_sections)} canned discussion sections.")
except Exception as e:
    print(f"⚠️ Failed to insert canned discussion sections: {e}")

# === Load JSON template for header positions ===
with open(input_json, "r", encoding="utf-8") as f:
    data = json.load(f)

page_width = data.get("page_width", 612)
page_height = data.get("page_height", 792)

if "text_blocks" not in data:
    raise ValueError("Template JSON must contain 'text_blocks' list for header layout reference.")

text_blocks = data["text_blocks"]

# Build word list
word_list = []
for w in text_blocks:
    if "text" in w and w["text"].strip():
        rl_y = page_height - w["top"]
        word_list.append({
            "text": w["text"].strip(),
            "x": w["x0"],
            "y": rl_y,
            "font": HEADER_FONT,
            "size": HEADER_SIZE
        })

template_phrases = [
    ["Report", "for", "State", "Farm", "Insurance"],
    ["Re.", "Inspection", "of", "Carlisle", "Residence"],
    ["2238", "Elderslie", "Drive,", "Germantown,", "Tennessee"],
    ["42-89G4-23R"]
]

def find_phrase_positions(words, phrases):
    matches = []
    texts = [w["text"] for w in words]
    for phrase in phrases:
        plen = len(phrase)
        for i in range(len(words) - plen + 1):
            if texts[i:i+plen] == phrase:
                first = words[i]
                matches.append({
                    "original_phrase": " ".join(phrase),
                    "x": first["x"],
                    "y": first["y"],
                    "font": first.get("font", HEADER_FONT),
                    "size": first.get("size", HEADER_SIZE),
                    "start_idx": i,
                    "end_idx": i + plen - 1
                })
                break
    return matches

matched_fields = find_phrase_positions(word_list, template_phrases)
for f in matched_fields:
    f["new_text"] = header_replacements.get(f["original_phrase"], f["original_phrase"])

address_field = next((f for f in matched_fields if f["original_phrase"] == "2238 Elderslie Drive, Germantown, Tennessee"), None)
id_field = next((f for f in matched_fields if f["original_phrase"] == "42-89G4-23R"), None)

if id_field:
    id_text = id_field.get("new_text", id_field["original_phrase"])
    id_x_end = id_field["x"] + stringWidth(id_text, id_field["font"], id_field["size"])
else:
    id_x_end = None

# === Text wrapping helpers ===
def wrap_paragraph_to_lines(paragraph, font_name, font_size, max_width):
    words = paragraph.split()
    lines = []
    current = ""
    for word in words:
        candidate = word if current == "" else current + " " + word
        if stringWidth(candidate, font_name, font_size) <= max_width:
            current = candidate
        else:
            if current == "":
                part = ""
                for ch in word:
                    if stringWidth(part + ch, font_name, font_size) <= max_width:
                        part += ch
                    else:
                        if part:
                            lines.append(part)
                        part = ch
                current = part
            else:
                lines.append(current)
                current = word
    if current:
        lines.append(current)
    return lines

def wrap_text_preserve_paragraphs(text, font_name, font_size, max_width):
    paragraphs = text.split("\n\n")
    all_lines = []
    for p in paragraphs:
        p = p.strip()
        if p == "":
            all_lines.append("")
            continue
        lines = wrap_paragraph_to_lines(p, font_name, font_size, max_width)
        all_lines.extend(lines)
        all_lines.append("")
    if all_lines and all_lines[-1] == "":
        all_lines.pop()
    return all_lines

# === Text area width and underline calculation ===
if address_field and id_x_end:
    underline_x_start = address_field["x"]
    underline_x_end = id_x_end
    if underline_x_end <= underline_x_start + 20:
        underline_x_start = LEFT_MARGIN
        underline_x_end = page_width - RIGHT_MARGIN
else:
    underline_x_start = LEFT_MARGIN
    underline_x_end = page_width - RIGHT_MARGIN

min_underline_length = 464.57
current_length = underline_x_end - underline_x_start
if current_length < min_underline_length:
    underline_x_end = underline_x_start + min_underline_length
    if underline_x_end > page_width - RIGHT_MARGIN:
        underline_x_end = page_width - RIGHT_MARGIN
        underline_x_start = underline_x_end - min_underline_length

text_area_width = underline_x_end - underline_x_start
line_height = BODY_SIZE * 1.3

use_sections = bool(sections) and isinstance(sections, list) and len(sections) > 0
if not use_sections:
    sections = [{"heading": "INSPECTION REPORT", "content": "Your full body text here..."}]

# === PDF Generation ===
c = canvas.Canvas(output_pdf, pagesize=(page_width, page_height))
current_page = 1
current_y = None

def draw_header(c_obj):
    for f in matched_fields:
        c_obj.setFont(f.get("font", HEADER_FONT), f.get("size", HEADER_SIZE))
        c_obj.setFillColor(gray)
        c_obj.drawString(f["x"], f["y"], f.get("new_text", f["original_phrase"]))
    c_obj.setStrokeColor(black)
    c_obj.setLineWidth(1.5)
    c_obj.line(underline_x_start, (address_field["y"] - 2) if address_field else page_height - 100,
               underline_x_end, (address_field["y"] - 2) if address_field else page_height - 100)
    c_obj.setFillColor(black)

def draw_page_number(c_obj, current_page):
    c_obj.setFont(BODY_FONT, BODY_SIZE)
    c_obj.setFillColor(black)
    c_obj.drawCentredString(page_width / 2, PAGE_NUMBER_Y, f"Page {current_page}")
    c_obj.setFillColor(black)

def start_new_page_with_header(new_page=False):
    global current_page, c
    if new_page:
        draw_page_number(c, current_page)
        c.showPage()
        current_page += 1
    draw_header(c)
    if address_field:
        base_y = address_field["y"]
    else:
        base_y = page_height - 80
    return base_y - 30

# Draw header for first page
current_y = start_new_page_with_header(new_page=False)

# --- New helper: render multiple images in a line ---
def render_images_line(c_obj, images_list, current_y_pos, max_width, x_start):
    left_images, right_images, center_images = [], [], []
    for img_obj in images_list:
        align = img_obj.get("align", "center").lower()
        if align == "left":
            left_images.append(img_obj)
        elif align == "right":
            right_images.append(img_obj)
        else:
            center_images.append(img_obj)

    def load_img_info(img_obj):
        img_file = img_obj.get("path")
        img = ImageReader(img_file)
        w, h = img.getSize()
        scale = min(max_width / w, 1)
        return {"img": img, "width": w * scale, "height": h * scale}

    left_info = [load_img_info(img) for img in left_images]
    right_info = [load_img_info(img) for img in right_images]
    center_info = [load_img_info(img) for img in center_images]

    max_img_height = max(
        [info["height"] for info in left_info + right_info + center_info] or [0]
    )

    if current_y_pos - max_img_height < BOTTOM_MARGIN:
        current_y_pos = start_new_page_with_header(new_page=True)

    # Draw left-aligned images
    x_cursor = x_start
    for info in left_info:
        c_obj.drawImage(info["img"], x_cursor, current_y_pos - info["height"],
                        width=info["width"], height=info["height"])
        x_cursor += info["width"] + 5

    # Draw right-aligned images
    x_cursor = x_start + max_width
    for info in reversed(right_info):
        x_cursor -= info["width"]
        c_obj.drawImage(info["img"], x_cursor, current_y_pos - info["height"],
                        width=info["width"], height=info["height"])
        x_cursor -= 5

    # Draw center-aligned images
    total_center_width = sum(info["width"] for info in center_info) + 5 * (len(center_info)-1)
    x_cursor = x_start + (max_width - total_center_width) / 2
    for info in center_info:
        c_obj.drawImage(info["img"], x_cursor, current_y_pos - info["height"],
                        width=info["width"], height=info["height"])
        x_cursor += info["width"] + 5

    return current_y_pos - max_img_height - line_height

# --- New helper: draw fully justified line ---
def draw_justified_line(c_obj, line, x_start, y_pos, font_name, font_size, max_width):
    words = line.split()
    if not words:
        return

    line_width = sum([stringWidth(w, font_name, font_size) for w in words])
    if line_width / max_width >= 0.8 and len(words) > 1:
        num_gaps = len(words) - 1
        extra_space = (max_width - line_width) / num_gaps
        x = x_start
        for i, word in enumerate(words):
            c_obj.drawString(x, y_pos, word)
            x += stringWidth(word, font_name, font_size) + extra_space
    else:
        c_obj.drawString(x_start, y_pos, line)

# === Render Sections ===
for sec_idx, section in enumerate(sections):
    heading = section.get("heading", "").strip()
    content = section.get("content", "")
    subsections = section.get("subsections", [])
    image_path = section.get("image_path", None)
    left_image_path = section.get("left_image_path", None)


    # --- Special handling for Disclaimer ---
    if heading.lower() == "disclaimer":
        # Initialize a local y cursor from global
        current_y_pos = current_y
        if not disclaimer_heading_drawn:
            c.setFont(HEADING_FONT, HEADING_SIZE)
            c.setFillColor(black)
            c.drawString(underline_x_start, current_y_pos, heading)
            heading_text_width = stringWidth(heading, HEADING_FONT, HEADING_SIZE)
            c.setStrokeColor(gray)
            c.setLineWidth(0.5)
            c.line(underline_x_start, current_y_pos - 2, underline_x_start + heading_text_width, current_y_pos - 2)
            c.setStrokeColor(black)
            disclaimer_heading_drawn = True
            current_y_pos -= HEADING_SPACING
            current_x = underline_x_start
        else:
            current_x = underline_x_start

        if content:
            c.setFont(BODY_FONT, BODY_SIZE)
            words = content.split()
            line = ""
            max_width_for_content = text_area_width

            idx = 0
            while idx < len(words):
                test_line = (line + " " + words[idx]).strip() if line else words[idx]
                if stringWidth(test_line, BODY_FONT, BODY_SIZE) <= max_width_for_content:
                    line = test_line
                    idx += 1
                else:
                    # page break if needed
                    if current_y_pos - line_height < BOTTOM_MARGIN:
                        current_y_pos = start_new_page_with_header(new_page=True)
                        c.setFont(BODY_FONT, BODY_SIZE)      # ✅ RESET FONT AFTER PAGE BREAK
                        c.setFillColor(black)
                        current_x = underline_x_start
                        max_width_for_content = text_area_width
                    draw_justified_line(c, line, current_x, current_y_pos, BODY_FONT, BODY_SIZE, max_width_for_content)
                    current_y_pos -= line_height
                    line = ""  # reset accumulation
                    current_x = underline_x_start
                    max_width_for_content = text_area_width

            if line:
                if current_y_pos - line_height < BOTTOM_MARGIN:
                    current_y_pos = start_new_page_with_header(new_page=True)
                    c.setFont(BODY_FONT, BODY_SIZE)      # ✅ RESET FONT AFTER PAGE BREAK
                    c.setFillColor(black)
                    current_x = underline_x_start
                    max_width_for_content = text_area_width
                    
                draw_justified_line(c, line, current_x, current_y_pos, BODY_FONT, BODY_SIZE, max_width_for_content)
                current_y_pos -= line_height * PARAGRAPH_SPACING_MULTIPLIER

        # Sync back to global cursor and reset X to avoid shift for next sections
        current_y = current_y_pos
        current_x = underline_x_start
        continue
    # --- Normal section rendering ---
    sec_lines = wrap_text_preserve_paragraphs(content, BODY_FONT, BODY_SIZE, text_area_width)
    heading_space = HEADING_SIZE * 1.2 + 8

    skip_heading = heading.lower() == "client communication & closing note"
    if not skip_heading:
        if current_y - heading_space < BOTTOM_MARGIN:
            current_y = start_new_page_with_header(new_page=True)
        c.setFont(HEADING_FONT, HEADING_SIZE)
        c.setFillColor(black)
        text_width = stringWidth(heading, HEADING_FONT, HEADING_SIZE)
        center_x = (underline_x_start + underline_x_end - text_width) / 2
        c.drawString(center_x, current_y, heading)
        current_y -= heading_space

    # --- Render main content with justification ---
    c.setFont(BODY_FONT, BODY_SIZE)
    c.setFillColor(black)
    idx = 0
    while idx < len(sec_lines):
        line = sec_lines[idx]
        is_par_break = (line == "")
        required_line_space = line_height * PARAGRAPH_SPACING_MULTIPLIER if is_par_break else line_height
        if current_y - required_line_space < BOTTOM_MARGIN:
            current_y = start_new_page_with_header(new_page=True)
            c.setFont(BODY_FONT, BODY_SIZE)
            c.setFillColor(black)
        if is_par_break:
            current_y -= line_height * PARAGRAPH_SPACING_MULTIPLIER
        else:
            draw_justified_line(c, line, underline_x_start, current_y, BODY_FONT, BODY_SIZE, text_area_width)
            current_y -= line_height
        idx += 1

    # --- Subsections rendering ---
    for sub in subsections:
        sub_heading = sub.get("heading", "").strip()
        sub_content = sub.get("content", "")
        if current_y - heading_space < BOTTOM_MARGIN:
            current_y = start_new_page_with_header(new_page=True)
        c.setFont(HEADING_FONT, HEADING_SIZE)
        c.setFillColor(black)
        c.drawString(underline_x_start, current_y, sub_heading)
        current_y -= heading_space

        sub_lines = wrap_text_preserve_paragraphs(sub_content, BODY_FONT, BODY_SIZE, text_area_width)
        c.setFont(BODY_FONT, BODY_SIZE)
        c.setFillColor(black)
        idx = 0
        while idx < len(sub_lines):
            line = sub_lines[idx]
            is_par_break = (line == "")
            required_line_space = line_height * PARAGRAPH_SPACING_MULTIPLIER if is_par_break else line_height
            if current_y - required_line_space < BOTTOM_MARGIN:
                current_y = start_new_page_with_header(new_page=True)
                c.setFont(BODY_FONT, BODY_SIZE)
                c.setFillColor(black)
            if is_par_break:
                current_y -= line_height * PARAGRAPH_SPACING_MULTIPLIER
            else:
                draw_justified_line(c, line, underline_x_start, current_y, BODY_FONT, BODY_SIZE, text_area_width)
                current_y -= line_height
            idx += 1

    # --- Image rendering ---
    if heading.lower() == "client communication & closing note" and left_image_path and image_path:
        left_img = ImageReader(left_image_path)
        l_img_width, l_img_height = left_img.getSize()
        if l_img_width > text_area_width / 2:
            scale = (text_area_width / 2) / l_img_width
            l_img_width *= scale
            l_img_height *= scale

        center_img = ImageReader(image_path)
        c_img_width, c_img_height = center_img.getSize()
        if c_img_width > text_area_width / 2:
            scale = (text_area_width / 2) / c_img_width
            c_img_width *= scale
            c_img_height *= scale

        max_img_height = max(l_img_height, c_img_height)
        if current_y - max_img_height < BOTTOM_MARGIN:
            current_y = start_new_page_with_header(new_page=True)

        left_img_x = underline_x_start
        left_img_y = current_y - l_img_height
        c.drawImage(left_img, left_img_x, left_img_y, width=l_img_width, height=l_img_height)

        center_img_x = underline_x_start + text_area_width - c_img_width
        center_img_y = current_y - c_img_height
        c.drawImage(center_img, center_img_x, center_img_y, width=c_img_width, height=c_img_height)

        current_y -= max_img_height + line_height
    else:
        if image_path:
            img = ImageReader(image_path)
            img_width, img_height = img.getSize()
            max_img_width = text_area_width
            if img_width > max_img_width:
                scale = max_img_width / img_width
                img_width *= scale
                img_height *= scale
            if current_y - img_height < BOTTOM_MARGIN:
                current_y = start_new_page_with_header(new_page=True)
            img_x = underline_x_start + (text_area_width - img_width) / 2
            img_y = current_y - img_height
            c.drawImage(img, img_x, img_y, width=img_width, height=img_height)
            current_y = img_y - line_height

    # --- Extra spacing between sections ---
    if sec_idx < len(sections) - 1:
        current_y -= line_height * PARAGRAPH_SPACING_MULTIPLIER

# Draw final page number and save
draw_page_number(c, current_page)
c.save()
print(f"✅ PDF generated: {output_pdf}")