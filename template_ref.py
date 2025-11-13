import os
import sys
import json
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.lib.colors import blue

OUTPUT_DIR = os.path.join(os.getcwd(), "output_template")
output_paths=os.path.join(OUTPUT_DIR, "output_ref.pdf")
REFERENCES_DIR = os.path.join(os.getcwd(), "references")
full_images = os.path.join(REFERENCES_DIR, "page14_img19.jpeg")

PAGE_WIDTH, PAGE_HEIGHT = 612, 792

# --- Coordinates from your JSON layout ---
text_coords = {
    "address": {"x": 93.6, "y": PAGE_HEIGHT - 32.391},  # client_name
    "code": {"x": 468.405, "y": PAGE_HEIGHT - 32.391},  # claim_number
}

logo_coords = {
    "x": 288.0,
    "y": PAGE_HEIGHT - 792 + 747.0,  # Adjusted for reportlab origin
    "width": 45,
    "height": 45,
    "path": full_images  # Replace with your logo path
}

# --- Function to draw a single page ---
def draw_page(c, user_texts, user_images):
    # Draw logo
    try:
        logo_img = ImageReader(logo_coords["path"])
        c.drawImage(
            logo_img,
            logo_coords["x"],
            logo_coords["y"],
            width=logo_coords["width"],
            height=logo_coords["height"],
            preserveAspectRatio=True,
            mask='auto'
        )
    except:
        print("Logo not found or failed to load.")

    # Draw user text fields in blue
    c.setFillColor(blue)
    if "client_name" in user_texts:
        c.drawString(text_coords["address"]["x"], text_coords["address"]["y"], user_texts["client_name"])
    if "claim_number" in user_texts:
        c.drawString(text_coords["code"]["x"], text_coords["code"]["y"], user_texts["claim_number"])
    c.setFillColorRGB(0, 0, 0)

    # Draw images (max 2 per page)
    max_images_per_page = 2
    image_width = 400
    image_height = 300
    spacing = 10

    y_start = logo_coords["y"] - image_height - spacing

    for idx, img_info in enumerate(user_images[:max_images_per_page]):
        img_path = img_info.get("path", "")
        caption = str(img_info.get("caption", ""))  # ensure string

        x_pos = (PAGE_WIDTH - image_width) / 2
        y_pos = y_start - idx * (image_height + spacing + 15)

        try:
            if img_path and os.path.exists(img_path):
                c.drawImage(img_path, x_pos, y_pos, width=image_width, height=image_height, preserveAspectRatio=True, mask='auto')
            else:
                print(f"Image not found: {img_path}")
        except Exception as e:
            print(f"Failed to load image: {img_path}. Error: {e}")

        # Draw caption centered under image
        caption_width = c.stringWidth(caption)
        caption_x = x_pos + (image_width - caption_width) / 2
        c.drawString(caption_x, y_pos - 15, caption)

# --- Load user_images from captions.json ---
def load_user_images(uploads_folder):
    captions_file = os.path.join(uploads_folder, "captions.json")
    if not os.path.exists(captions_file):
        print(f"{captions_file} not found. No images will be added.")
        return []

    with open(captions_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Sort by order
    data.sort(key=lambda x: x.get("order", 0))

    # Only reference type images with caption fallback
    user_images = []
    for item in data:
        if item.get("type") == "reference":
            caption = item.get("rewritten_caption") or item.get("enhanced_caption") or item.get("original_caption") or ""
            user_images.append({
                "path": item.get("filepath", ""),
                "caption": str(caption)  # ensure string
            })

    return user_images

# --- Main function to create PDF ---
# --- Main function to create PDF ---
def create_pdf(output_path, uploads_folder, user_texts):
    user_images = load_user_images(uploads_folder)

    if not user_images:
        print("No reference images found. PDF will not be generated.")
        return  # skip PDF creation

    c = canvas.Canvas(output_path, pagesize=letter)

    images_per_page = 2
    for i in range(0, len(user_images), images_per_page):
        draw_page(c, user_texts, user_images[i:i+images_per_page])
        c.showPage()

    c.save()
    print(f"PDF saved to {output_path}")


# --- Entry point ---
if __name__ == "__main__":
    # Read JSON input from subprocess arguments
    if len(sys.argv) > 1:
        try:
            input_data = json.loads(sys.argv[1])
        except Exception as e:
            print("Invalid input JSON:", e)
            input_data = {}
    else:
        input_data = {}

    user_texts = {
        "client_name": input_data.get("client_name", "INPUT_CLIENT_NAME"),
        "claim_number": input_data.get("claim_number", "INPUT_CLAIM_NUMBER")
    }

    uploads_folder = "uploads"  # path to your uploads folder
    create_pdf(output_paths, uploads_folder, user_texts)
