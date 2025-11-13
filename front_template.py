import os
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import black, red, blue



REFERENCES_DIR = os.path.join(os.getcwd(), "references")
full_image = os.path.join(REFERENCES_DIR, "page1_img1.jpeg")

# -----------------------
# 1️⃣ Font Registration
def register_fonts():
    # 1. Fonts included in your Docker image (/app/fonts/)
    docker_font_path = os.path.join(os.getcwd(), "fonts", "calibrib.ttf")

    # 2. Common Linux font locations inside Docker
    linux_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]

    # 3. Windows fallback (only used if running locally)
    windows_paths = [
        "C:/Windows/Fonts/calibrib.ttf",
        "C:/Windows/Fonts/arialbd.ttf"
    ]

    # === CHECK DOCKER/CUSTOM FONTS FIRST ===
    if os.path.exists(docker_font_path):
        pdfmetrics.registerFont(TTFont("Custom-Bold", docker_font_path))
        return "Custom-Bold"

    # === CHECK LINUX SYSTEM FONTS ===
    for path in linux_paths:
        if os.path.exists(path):
            pdfmetrics.registerFont(TTFont("Linux-Bold", path))
            return "Linux-Bold"

    # === CHECK WINDOWS FONTS (LOCAL DEV) ===
    for path in windows_paths:
        if os.path.exists(path):
            pdfmetrics.registerFont(TTFont("Windows-Bold", path))
            return "Windows-Bold"

    # === FINAL FALLBACK (ALWAYS AVAILABLE) ===
    return "Times-Bold"


# -----------------------
# 2️⃣ Text Wrapping
def wrap_text(text, font_name, font_size, max_width, max_words_per_line=None):
    if max_words_per_line:
        words = text.split()
        return [' '.join(words[i:i + max_words_per_line]) for i in range(0, len(words), max_words_per_line)]
    else:
        words = text.split()
        lines = []
        current_line = ""
        for word in words:
            test_line = f"{current_line} {word}".strip()
            test_width = pdfmetrics.stringWidth(test_line, font_name, font_size)
            if test_width <= max_width or not current_line:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
        return lines

# -----------------------
# 3️⃣ Draw Text Centered
def draw_bold_text_centered_page(c, page_width, y, lines, font_name, font_size, line_height=None, debug=False):
    if line_height is None:
        line_height = font_size * 1.25
    boxes = []
    page_center_x = page_width / 2
    current_y = y
    c.setFillColor(black)
    c.setFont(font_name, font_size)
    for line in lines:
        text_width = pdfmetrics.stringWidth(line, font_name, font_size)
        x_start = page_center_x - text_width / 2
        for dx, dy in [(0, 0), (0.15, 0.1)]:
            c.drawString(x_start + dx, current_y + dy, line)
        if debug:
            c.setStrokeColor(red)
            c.rect(x_start, current_y, text_width, line_height, stroke=1, fill=0)
        boxes.append([x_start, current_y, text_width, line_height])
        current_y -= line_height
    return boxes, len(lines)

# -----------------------
# 4️⃣ Box Overlap Detection
def boxes_overlap(box1, box2):
    x1, y1, w1, h1 = box1
    x2, y2, w2, h2 = box2
    tolerance = 0.1
    return not (x1 + w1 <= x2 + tolerance or x2 + w2 <= x1 + tolerance or y1 + h1 <= y2 + tolerance or y2 + h2 <= y1 + tolerance)

# -----------------------
# 5️⃣ Draw Images
def draw_images_from_json(c, images, page_height, background_image, overlay_image, debug=False):
    overlay_info = None
    for i, img in enumerate(images):
        x = img["x0"]
        y = page_height - img["y1"]
        w = img["width"]
        h = img["height"]
        if i == 0 and os.path.exists(background_image):
            c.drawImage(background_image, x, y, width=w, height=h)
        elif i == 1 and os.path.exists(overlay_image):
            overlay_info = {"x": x, "y": y, "w": w, "h": h}
    return overlay_info

# -----------------------
# 6️⃣ Draw Foreground Image
def draw_foreground_image(c, overlay_info, overlay_image, drawn_text_boxes, debug=False):
    if overlay_info and os.path.exists(overlay_image):
        overlay_x = overlay_info["x"]
        overlay_y = overlay_info["y"]
        overlay_w = overlay_info["w"]
        overlay_h = overlay_info["h"]
        adjusted_overlay_y = overlay_y
        max_attempts = 50
        overlap_detected = True
        while overlap_detected and max_attempts > 0:
            overlap_detected = False
            overlay_box = [overlay_x, adjusted_overlay_y, overlay_w, overlay_h]
            for text_box in drawn_text_boxes:
                if boxes_overlap(overlay_box, text_box):
                    overlap_detected = True
                    adjusted_overlay_y -= 5
                    break
            max_attempts -= 1
        c.drawImage(overlay_image, overlay_x, adjusted_overlay_y, width=overlay_w, height=overlay_h)
        if debug:
            c.setStrokeColor(blue)
            c.rect(overlay_x, overlay_y, overlay_w, overlay_h, stroke=1, fill=0)
        return {"x": overlay_x, "y": adjusted_overlay_y, "w": overlay_w, "h": overlay_h}
    return overlay_info

# -----------------------
# 7️⃣ Hardcoded Coordinates & Widths
TEXT_COORDS = {
    "address": {"x0": 244.92, "top": 580.52, "width": 400},
    "claim_number": {"x0": 314.90, "top": 630.20, "width": 150},
    "company": {"x0": 240.48, "top": 282.44, "width": 200},
    "date": {"x0": 247.32, "top": 183.08, "width": 150},
    "email": {"x0": 197.88, "top": 315.56, "width": 250},
    "file_number": {"x0": 333.44, "top": 696.44, "width": 100},
    "insured_person": {"x0": 278.39, "top": 613.64, "width": 200},
    "loss_date": {"x0": 343.95, "top": 646.76, "width": 120},
    "person": {"x0": 296.60, "top": 298.99, "width": 150}
}

# -----------------------
# 8️⃣ Render PDF
# -----------------------
# 8️⃣ Render PDF (updated to accept overlay image path and output path)
def render_pdf(output_pdf_path, overlay_image_path, page_width, page_height, new_values, font_size=12, debug=False):
    font_name = register_fonts()
    line_height = font_size * 1.25
    c = canvas.Canvas(output_pdf_path, pagesize=(page_width, page_height))
    drawn_text_boxes = []

    # Images (background is still hardcoded, overlay is dynamic)
    images_json = [
        {"x0": 11.94, "y0": 15.54, "x1": 600.0, "y1": 776.52, "width": 588.06, "height": 760.98},
        {"x0": 118.95, "y0": 294.47, "x1": 485.03, "y1": 431.78, "width": 366.08, "height": 137.31}
    ]
    background_image = full_image  # can also make this dynamic if needed
    overlay_image = overlay_image_path
    overlay_info = draw_images_from_json(c, images_json, page_height, background_image, overlay_image, debug)

    # Static text just above the address
    if "address" in TEXT_COORDS:
        addr_coord = TEXT_COORDS["address"]
        y_draw = page_height - addr_coord["top"] + line_height
        lines = ["Re: Residence Located At"]
        boxes, _ = draw_bold_text_centered_page(c, page_width, y_draw, lines, font_name, font_size, line_height, debug)
        drawn_text_boxes.extend(boxes)

    # Draw fixed-position "Report For:" at given coordinates
    report_x0 = 270.0
    report_top = 232.76
    report_y = page_height - report_top
    c.setFont(font_name, font_size)
    c.setFillColor(black)
    c.drawString(report_x0, report_y, "Report For:")

    # Draw all other fields
    for field, val in new_values.items():
        if field not in TEXT_COORDS:
            continue

        prefix = ""
        max_words_per_line = None

        if field == "person":
            prefix = "Attention: "
        elif field == "insured_person":
            prefix = "Insured: "
        elif field == "loss_date":
            prefix = "Reported Date of Loss: "
        elif field == "claim_number":
            prefix = "Claim Number: "
        elif field == "file_number":
            prefix = "WIE File Number: "
        elif field == "address":
            max_words_per_line = 8

        coord = TEXT_COORDS[field]
        max_width = coord["width"]
        y_top = coord["top"]
        y_draw = page_height - y_top

        # Wrap text without prefix first
        lines = wrap_text(str(val), font_name, font_size, max_width, max_words_per_line)

        # Attach prefix only to the first line
        if prefix and lines:
            lines[0] = prefix + lines[0]

        # Calculate boxes for overlap
        current_text_boxes = []
        current_y = y_draw
        page_center_x = page_width / 2
        for line in lines:
            text_width = pdfmetrics.stringWidth(line, font_name, font_size)
            x_start = page_center_x - text_width / 2
            current_text_boxes.append([x_start, current_y, text_width, line_height])
            current_y -= line_height

        # Shift to avoid overlap
        shifted_boxes = []
        shift_amount = 0
        max_attempts = 100
        overlap_detected = True

        while overlap_detected and max_attempts > 0:
            overlap_detected = False
            tentative_boxes = [[box[0], box[1] - shift_amount, box[2], box[3]] for box in current_text_boxes]
            for t_box in tentative_boxes:
                for d_box in drawn_text_boxes:
                    if boxes_overlap(t_box, d_box):
                        overlap_detected = True
                        shift_amount += line_height
                        break
                if overlap_detected:
                    break
            max_attempts -= 1
        shifted_boxes = [[box[0], box[1] - shift_amount, box[2], box[3]] for box in current_text_boxes]

        # Draw bold black text
        c.setFillColor(black)
        c.setFont(font_name, font_size)
        current_y_draw = y_draw - shift_amount
        for line in lines:
            text_width = pdfmetrics.stringWidth(line, font_name, font_size)
            x_start = page_center_x - text_width / 2
            for dx, dy in [(0, 0), (0.15, 0.1)]:
                c.drawString(x_start + dx, current_y_draw + dy, line)
            current_y_draw -= line_height

        drawn_text_boxes.extend(shifted_boxes)

    # Foreground image
    overlay_info = draw_foreground_image(c, overlay_info, overlay_image, drawn_text_boxes, debug)
    c.showPage()
    c.save()
    print(f"✅ PDF saved: {output_pdf_path}")
