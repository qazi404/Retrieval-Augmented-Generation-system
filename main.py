import subprocess
from front_template import render_pdf 
import openai
from openai import OpenAI
import chromadb
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.responses import FileResponse, Response
from fastapi.responses import JSONResponse
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from dotenv import load_dotenv
from fastapi import UploadFile, File ,Form
from zipfile import ZipFile
import tempfile
import fitz
import glob
import uuid
import re
import os
import json
import shutil
import sys
import spacy
from spacy.util import is_package
from typing import List, Optional
from fastapi.responses import FileResponse
import sqlite3
from fastapi import Depends
from pydantic import BaseModel
import asyncio
import requests
from datetime import datetime




# Global variable to store last submitted fields
LAST_READ_FIELDS_PAYLOAD = {}
LAST_UPLOADED_FRONT_IMAGE = ""
LAST_UPLOADED_REFERENCE_IMAGES = []

REFERENCES_DIR = os.path.join(os.getcwd(), "references")
output_front = os.path.join(os.getcwd(), "output_template")
outputpath_temp=os.path.join(output_front, "front_temp.pdf")
input_json = os.path.join(REFERENCES_DIR, "page_1.json")
ref=os.path.join(REFERENCES_DIR, "mapping(2).json")
full_image = os.path.join(REFERENCES_DIR, "page1_img1.jpeg")
final_path = os.path.join(os.getcwd(), "output_template")
final_pdf=os.path.join(final_path, "final_report.pdf")


def extract_selected_fields():

    global LAST_READ_FIELDS_PAYLOAD

    def flatten_payload(payload, parent_key=""):
        """Recursively flatten nested dicts."""
        flat = {}
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except Exception:
                flat[parent_key or "raw_text"] = payload
                return flat
        if isinstance(payload, dict):
            for k, v in payload.items():
                new_key = f"{parent_key}_{k}" if parent_key else k
                if isinstance(v, dict):
                    flat.update(flatten_payload(v, new_key))
                else:
                    flat[new_key] = v
        else:
            flat[parent_key or "raw_text"] = payload
        return flat

    flat_payload = flatten_payload(LAST_READ_FIELDS_PAYLOAD)

    def get_field(*candidates):
        """Return the first existing non-empty field value."""
        for key in candidates:
            val = flat_payload.get(key)
            if val and str(val).strip():
                return str(val).strip()
        return ""

    # === Extract the required fields ===
    client_name = get_field("header_client_name", "client_name", "header_client", "client")
    insured_name = get_field("header_insured_name", "insured_name", "insured")
    claim_number = get_field("header_claim_number", "claim_number", "claim_no", "claim")
    canned_discussion = get_field("canned_discussion_to_include", "canned_discussion", "canned_discussion_to_include")
    address =get_field("header_insured_address","insured_address","insured")
    # Debug output
    print("=== Extracted Field Values ===")
    print(f"Client Name: {client_name}")
    print(f"Insured Name: {insured_name}")
    print(f"Claim Number: {claim_number}")
    print(f"Canned Discussion: {canned_discussion}")
    print(f"ADDRESS: {address}")
    print("===============================")

    return client_name, insured_name, claim_number, canned_discussion,address

def trigger_page_generation():
    client_name, insured_name, claim_number, canned_discussion,address= extract_selected_fields()
        
    payload={
        "client_name":client_name,
        "insured_name":insured_name,
        "claim_number":claim_number,
        "heading":canned_discussion,
        "address":address
          } 
    subprocess.run(["python","content_templating.py",json.dumps(payload)])

def trigger_ref_generation():
    client_name, insured_name, claim_number, canned_discussion,address= extract_selected_fields()
        
    payload={
        "client_name":client_name,
        "insured_name":insured_name,
        "claim_number":claim_number,
        "heading":canned_discussion,
        "address":address
          } 
    subprocess.run(["python","template_ref.py",json.dumps(payload)])
        
def build_pdf_values_from_last_payload():
    global LAST_READ_FIELDS_PAYLOAD, LAST_UPLOADED_FRONT_IMAGE

    def flatten_payload(payload, parent_key=""):
        """Recursively flatten nested dicts."""
        flat = {}
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except Exception:
                flat[parent_key or "raw_text"] = payload
                return flat
        if isinstance(payload, dict):
            for k, v in payload.items():
                new_key = f"{parent_key}_{k}" if parent_key else k
                if isinstance(v, dict):
                    flat.update(flatten_payload(v, new_key))
                else:
                    flat[new_key] = v
        else:
            flat[parent_key or "raw_text"] = payload
        return flat

    # Flatten payload
    flat_payload = flatten_payload(LAST_READ_FIELDS_PAYLOAD)

    # Map PDF keys
    pdf_values = {
        "date": flat_payload.get("header_report_date") or flat_payload.get("report_date") or "INPUT DATE",
        "company": flat_payload.get("header_client_name") or flat_payload.get("client_name") or "INPUT COMPANY",
        "person": flat_payload.get("header_client_contact_name") or flat_payload.get("client_contact_name") or "INPUT CONTACT PERSON",
        "email": flat_payload.get("header_client_contact_email") or flat_payload.get("client_contact_email") or "INPUT EMAIL",
        "address": flat_payload.get("header_insured_address") or flat_payload.get("insured_address") or "INPUT ADDRESS",
        "insured_person": flat_payload.get("header_insured_name") or flat_payload.get("insured_name") or "INPUT INSURED PERSON",
        "claim_number": flat_payload.get("header_claim_number") or flat_payload.get("claim_number") or "INPUT CLAIM NUMBER",
        "loss_date": flat_payload.get("header_date_of_loss") or flat_payload.get("date_of_loss") or "INPUT LOSS DATE",
        "file_number": flat_payload.get("header_wie_file_number") or flat_payload.get("wie_file_number") or "INPUT FILE NUMBER"
    }

    # Debug print for matched keys
    print("=== PDF Values Mapping Debug ===")
    for k, v in pdf_values.items():
        matched_key = next((fk for fk in flat_payload.keys() if v == flat_payload[fk]), None)
        print(f"{k}: {v}  <-- matched key: {matched_key}")
    print("===============================")

    overlay_image_path = LAST_UPLOADED_FRONT_IMAGE if LAST_UPLOADED_FRONT_IMAGE else ""
    print(f"✅ Overlay image path: {overlay_image_path}")

    return pdf_values, overlay_image_path



# -----------------------------
# Main function: get PDF values + overlay image path
# -----------------------------



def trigger_pdf_generation():
    try:
        pdf_values, overlay_image_path = build_pdf_values_from_last_payload()
        page_json = input_json
        field_map_json = ref
        background_image = full_image
        output_pdf = outputpath_temp

        render_pdf(
            output_pdf,
            overlay_image_path,
            612, 
            792,
            pdf_values,
            font_size=12,
            debug=False
        )
    except Exception as e:
        print(f"⚠️ PDF generation failed but continuing: {e}")
        
        
def maybe_trigger_pdf():
    """
    Generate PDF if fields exist (fields are mandatory).
    Uses latest uploaded image if available.
    """
    global LAST_READ_FIELDS_PAYLOAD
    # if not LAST_READ_FIELDS_PAYLOAD:
    #     print("⚠️ Skipping PDF generation: No form fields available yet.")
    #     return
    trigger_pdf_generation()

# ----------------------------
# Load environment variables
# ----------------------------
load_dotenv()
openai_api_key = os.environ.get("OPENAI_API_KEY")
if openai_api_key:
    openai.api_key = openai_api_key


AIRTABLE_TOKEN = os.environ.get("AIRTABLE_TOKEN")
BASE_ID = os.environ.get("BASE_ID")
TABLE_ID = os.environ.get("TABLE_ID")
VIEW_ID = os.environ.get("VIEW_ID")
CLIENT_TABLE_ID = os.environ.get("CLIENT_TABLE_ID")

# ----------------------------
# Initialize FastAPI app
# ----------------------------



####fields ready####
app = FastAPI()

global_lock = asyncio.Lock()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # Allow all origins
    allow_credentials=True,   # Allow cookies/auth (optional)
    allow_methods=["*"],      # Allow all HTTP methods (GET, POST, OPTIONS, etc.)
    allow_headers=["*"],      # Allow all headers
)

# ----------------------------
# Configuration / Embedding
# ----------------------------
EMBEDDING_MODEL = "all-mpnet-base-v2"
embedding_func = SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)

FIELDS_M = [
    #"client_name",
    #"client_contact_name",
    #"client_contact_email",
    #"insured_name",
    #"insured_address",
    #"claim_number",
    #"wie_file_number",
    #"date_of_loss",
    #"inspection_date",
    #"prepared_by"
]

def mask_sensitive_fields(fields: dict) -> dict:
    """Recursively remove sensitive keys from dict."""
    if not isinstance(fields, dict):
        return fields
    sanitized = {}
    for k, v in fields.items():
        if k in FIELDS_M:
            continue
        if isinstance(v, dict):
            sanitized[k] = mask_sensitive_fields(v)
        else:
            sanitized[k] = v
    return sanitized

# ----------------------------
# Helper: open client & collection
# ----------------------------
def _get_vector_db_client_and_collection(collection_name: str):
    base_dir = os.path.dirname(__file__)
    db_dir = os.path.join(base_dir, "vectordatabase")
    os.makedirs(db_dir, exist_ok=True)

    client = chromadb.PersistentClient(path=db_dir)
    try:
        collection = client.get_collection(collection_name, embedding_function=embedding_func)
    except Exception as e:
        try:
            names = [c.name for c in client.list_collections()]
        except Exception:
            names = []
        raise HTTPException(
            status_code=404,
            detail=f"Collection '{collection_name}' not found. Available: {names}. Error: {e}"
        )
    return client, collection

# ----------------------------
# Helper: build prompt from fields
# ----------------------------
def _build_prompt_from_fields(fields: dict, prefix: str = "") -> str:
    parts = []
    for k, v in fields.items():
        key_path = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            parts.append(_build_prompt_from_fields(v, prefix=key_path))
        elif isinstance(v, list):
            list_str = ", ".join(str(i) for i in v)
            parts.append(f"{key_path}: {list_str}")
        else:
            try:
                s = str(v)
            except Exception:
                s = repr(v)
            parts.append(f"{key_path}: {s}")
    prompt = "\n".join(parts)
    return prompt[:8000]

# ----------------------------
# Helper: retrieve context from Chroma
# ----------------------------
def retrieve_context(collection, query_text, top_k=5):
    results = collection.query(query_texts=[query_text], n_results=top_k, include=["documents", "metadatas"])
    contexts = []
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    for d, m in zip(docs, metas):
        contexts.append({
            "text": d,
            "section": m.get("section"),
            "report_id": m.get("report_id")
        })
    return contexts


SECTION_RULES = {
     "purpose_and_objectives": """
    - STRICT LENGTH LIMIT: The entire section must be one concise paragraph (max 5 lines).
    - Summarize the assignment purpose briefly, using phrasing similar to “It is my understanding that our firm was to inspect the subject residence...”.
    - Also include the date you went to do inspection
    - Include the inspection purpose (e.g., tree impact, storm, fire) and general inspection scope (e.g., structural integrity, extent of damage).
    - Mention inspection activities (e.g., visual observation, leaning survey, elevation survey) in a single sentence only.
    - End with a sentence introducing the report’s contents (e.g., “What follows is a report of my site visit, observations, opinions, and recommendations.”).
    - DO NOT list objectives, dates, or claim details beyond what’s in the current case query.
    """,
 


"background_information": """
- Write 2–3 narrative-style paragraphs providing factual and contextual background for the inspection.
- Begin by describing the type, construction, and general setting of the building (e.g., “The subject residence is a two-story wood-framed structure with brick veneer exterior walls…”).
- Include details about the property surroundings and orientation (“The building is located on a gently sloping site and is surrounded by grassed lawns, perimeter shrubbery, and scattered trees.”).
- Mention the reason for the inspection and any known loss event (e.g., “It was reported that a tree fell onto the structure during a storm on August 19, 2025.”).
- Reference any conversations or third-party information obtained during the inspection (e.g., “During my site visit, I spoke with the repair contractor…”).
- Include reference to diagrams, drawings, or photographs if applicable (e.g., “Drawing Sheets -01 through -03 depict the roof and floor plans…”).
- Do NOT include analytical statements, opinions, or inspection results — this section is purely descriptive.
- Maintain a formal, third-person, investigative tone — avoid using “I observed” or “my inspection”; instead use “During the inspection…” or “The investigator noted…”.
- Each paragraph should flow narratively (3–5 sentences each) and reflect the professional style of Wehrman Investigative Engineering background sections.
- The section should read like a case introduction rather than an inspection summary.
"""

,


"inspection_observations": """
Write the 'Inspection Observations' section in the formal descriptive style of Wehrman Investigative Engineering (WIE) field reports.

- Use continuous narrative paragraphs only — no headings, numbering, or bullet points.
- Maintain impersonal third-person phrasing (e.g., “An inspection of the exterior revealed…”,
  “An examination of the interior indicated…”, “As shown in Photos 5 through 9…”). 
  Do NOT use “I” or “my inspection”.
- Structure the section in this logical order:
    1. Exterior observations (walls, roof, windows, exterior finishes, foundation perimeter)
    2. Main-level interior observations
    3. Upper-level interior observations
    4. Attic or roof framing observations
    5. Foundation or floor system conditions (if applicable)
    6. Measurement surveys or diagrams (digital-level, zip-level, drawings)
- Each paragraph should flow continuously, connecting related observations with commas or semicolons
  instead of short standalone sentences. Maintain WIE’s long-form technical rhythm.
- Use formal, factual statements describing only observed conditions. Avoid any analytical
  or causal language (e.g., no “consistent with”, “resulting from”, or “due to”).
- Include photographic references in parentheses within the narrative (e.g., “(Photos 8 through 10)”).
- Mention field measurement surveys or diagram references at the end of the section
  (e.g., “The results of the wall-lean and elevation surveys are shown on Drawing Sheets -04 through -06.”).
- Do not summarize overall condition or state conclusions — end with the last factual observation.
- Each paragraph should be 4–6 sentences long, mirroring the cadence of historical WIE inspection notes.
"""

,

"assessment": """
Write the 'Assessment' section in the formal analytical style used by Wehrman Investigative Engineering (WIE) technical reports.

- Provide 10–12 continuous paragraphs that analytically interpret the observed damages.
- Begin with a professional statement of opinion such as:
  “Based on my site visit and observations, it is my professional opinion that…”
- Maintain the professional first-person tone of a forensic structural engineer performing an insurance-related damage assessment.
- Use **cause-and-effect reasoning** to explain structural behavior (e.g., “The fractured rafters and wall plate separations were consistent with localized impact loading from the fallen tree.”).
- The writing should link observed facts to engineering interpretation — not restate the same observations from earlier sections.
- Follow the structured analytical flow used in historical reports:
  1. **Overall characterization** of the damage event and affected systems.
  2. **Roof framing** analysis (include counts, sizes, and percentages of affected area).
  3. **Ceiling framing** behavior and interaction with roof impact.
  4. **Wall and veneer** performance (lean, displacement, cracking, measurements).
  5. **Foundation and floor system** condition (survey findings, differential settlement, or lack thereof).
  6. **Global stability** and alignment evaluation (plumbness, racking, displacement).
  7. **Material condition analysis** (pre-existing splits, shrinkage, deterioration, insect damage, etc.).
  8. **Superficial or finish damages** (gutters, trim, shingles, flue, etc.).
  9. **Code compliance context** (state if damages are below IBC/IRC “substantial structural damage” threshold).
  10. **Final declarative opinion** confirming the structure’s stability and repairability.
- Include quantitative references where possible (e.g., “287 square feet,” “0.8 degrees,” “eleven percent of the total,” “Drawing Sheet -09”).
- Reference drawing sheets or measurement results when relevant, e.g., “as indicated on Drawing Sheet -07.”
- Reference building codes only when used to define thresholds or criteria (e.g., “below the threshold for substantial structural damage as defined by the IBC”).
- **Do NOT use prescriptive or directive repair phrases** such as “should be replaced,” “reset,” or “reinstalled.”  
  Instead, use professional judgment phrasing such as “can be repaired” or “is repairable.”
- Maintain objectivity; avoid adjectives like “severe” or “extensive.”
- Each paragraph should focus on one analytical component or system.
- **Do NOT include a summary paragraph beginning with phrases like ‘In summary,’ ‘Overall,’ or ‘To conclude.’**
- End the section with a firm, declarative engineering conclusion, such as:
  “The building remains structurally stable and repairable, and the damages are below the threshold for substantial structural damage as defined by the International Building Code.”
"""


,


"conclusions": """
- Reproduce the style and linguistic rhythm of the reference conclusions section **exactly**.
- Each bullet must directly mirror the phrasing structure of the source document, using
  openings such as “There was…” or “There were…” rather than “The structure exhibited…”.
- Provide 10–12 bullet points (not dashed points), each 1–3 sentences, matching the level of detail and
  component order of the reference (roof → ceiling → walls → finishes → foundation → overall stability).
- Preserve quantitative expressions (e.g., “22 rafters”, “15 feet length”, “1 percent of total”) from
  the scenario data or references; never generalize with terms like “several”, “some”, or “a number of”.
- Use precise engineering terminology exactly as shown in the reference reports:
  “top plate”, “pony wall”, “rafter tail”, “brick veneer cladding”, etc.
- Write in third-person technical narrative (e.g., “There was damage to…”), not in
  subjective or opinion-based voice.
- Do not summarize or rephrase. Reuse the reference phrasing wherever possible, replacing
  only variable data (names, locations, dimensions, quantities).
- Avoid introducing any recommendations, repair language, or code compliance opinions.
- End with one bullet confirming overall stability and repairability, in the exact
  phrasing pattern of the reference reports (e.g., “The building is structurally stable and it is repairable.”).
"""

,


"recommendations_for_repairs": """
Write the 'Recommendations for Repairs' section in the professional style of Wehrman Investigative Engineering (WIE) reports.

- Begin with a short introductory paragraph (2–3 sentences) stating that the structural damages can be repaired by resetting or replacing the damaged or displaced components, and reference the relevant drawing sheets if applicable (e.g., “as indicated on Drawing Sheets -07 through -09”).
  Example: “The structural damages can be repaired by resetting or replacing the damaged or displaced components. The recommended repairs are summarized as follows:”
   
- Follow with 6–8 bullet points (each on seperate line by a line space between them and also donot use - use this bullet mark •)  describing the required repairs. 
  Each bullet must be concise (1–2 sentences) and correspond directly to findings in the Assessment section.

- Use a variety of clear action verbs such as “Remove and replace,” “Reset,” “Repair,” “Cut out,” “Re-anchor,” or “Re-secure.”
  Avoid excessive repetition of the same verb.

- Keep the phrasing technical yet natural — each point should reflect engineering direction, not step-by-step contractor procedure.
  Example: “Remove and replace the brick veneer cladding as needed on the east elevation of the lower level, and reset the associated stud wall and top plate.”

- When relevant, group related work within a single bullet (e.g., “remove and replace roof framing and repair broken rafter tails”), as WIE reports often combine related actions per system.

- Reference the appropriate locations or components explicitly (e.g., “upper-level east wall,” “north elevation,” “northeast roof slope”), and mention drawing or photo references when available.

- Do NOT include procedural language, quality-control terms, or code compliance statements such as “in accordance with manufacturer’s instructions” or “meeting IBC requirements.”

- Do NOT end with a summary statement like “Upon completion…” — the final bullet should describe the last significant repair item and end cleanly, consistent with the style of WIE reference reports.
"""

,


"references": """
Write the 'References' section in the formal bibliographic format used by Wehrman Investigative Engineering (WIE) reports.

- Present each reference on its own line, separated by a single blank line. 
  (Each entry must be clearly separated and NOT combined into a single paragraph.)
- Do NOT number or use dashes; use simple paragraph-style or bulleted format with one reference per line.
  Example:
  Breyer, Donald E. *Design of Wood Structures.* New York: McGraw Hill, 1993.

  Faherty, Keith F. and Williamson, Thomas G. *Wood Engineering and Construction Handbook,* 2nd Edition. New York: McGraw Hill, 1995.

  Forest Products Laboratory. *Wood Handbook: Wood as an Engineering Material.* Madison, WI: U.S. Department of Agriculture, 1999.

- If redacted placeholders are present (e.g., [REDACTED_ORG], [REDACTED_PERSON]), replace them using your professional knowledge with the correct, standard references commonly cited in forensic structural engineering reports.
- Maintain proper bibliographic syntax:
  “Author(s). Title. Edition (if applicable). City: Publisher, Year.”
- Include relevant code references (IBC, IRC) for the applicable year.
- Include only standard, verifiable engineering and building code sources such as:
  - Breyer, Donald E. *Design of Wood Structures.* McGraw Hill, 1993.
  - Faherty, Keith F. and Williamson, Thomas G. *Wood Engineering and Construction Handbook,* 2nd Edition. McGraw Hill, 1995.
  - Forest Products Laboratory. *Wood Handbook: Wood as an Engineering Material.* U.S. Department of Agriculture, 1999.
  - International Code Council®. *International Building Code (IBC)* and *International Residential Code (IRC)*, latest applicable editions.
  - Petty, Stephen. *Forensic Engineering: Damage Assessments for Residential and Commercial Structures.* Taylor & Francis Group, 2013.
  - United States Gypsum Company. *Gypsum Construction Handbook.* U.S. Gypsum Co., 1992.
  - Wind Science and Engineering Center. *A Recommendation for an Enhanced Fujita Scale (EF-Scale).* Texas Tech University, 2006.
- Do NOT append any commentary or notes — list references only, cleanly formatted.
"""



}







def build_rag_prompt(query, context_chunks, section_name, debug_mode=False):
    # Build context text (unchanged)
    
    context_parts = []
    for c in context_chunks:
        report_id = c.get("report_id", "Unknown Report")
        section = c.get("section")
        if section:
            source_info = f"[From {report_id} - {section.replace('_', ' ').title()}]"
        else:
            source_info = f"[From {report_id}]"
        context_parts.append(f"{source_info}\n{c['text']}")
    context_text = "\n\n---\n\n".join(context_parts)

    # Normalize section key and fetch instructions
    key = section_name.strip().lower().replace(" ", "_")
    section_instructions = SECTION_RULES.get(key, "").strip()

    if debug_mode:
        # optional: include a short debug message in the prompt or log separately
        debug_note = f"\n\n[DEBUG] Section key: {key}\n"
    else:
        debug_note = ""

    prompt_messages = [
        {
            'role': 'system',
            'content': (
         f'You are a licensed forensic structural engineer and professional technical report writer and editor, '
         f'specializing in post-event damage assessments for insurance investigations. '
         f'You personally conduct site inspections and prepare reports for insurers such as State Farm '
         f'in the professional style of Wehrman Investigative Engineering.\n\n'

         f'Your task is to assemble a detailed, logically structured, and technically sound '
         f'"{section_name.replace("_", " ").title()}" section for a forensic engineering report '
         f'by reusing existing paragraphs and sentences from the reference documents.\n\n'

         f'Write in a formal, investigative tone as a consulting engineer who performed the inspection '
         f'(use "I" or "my inspection" where appropriate). Maintain the clear, professional style ' 
         f'seen in Wehrman Investigative Engineering reports—objective, factual, and technically precise.\n\n'

         f'Maintain the logical flow and order of the original reference text. '
         f'Do not add new interpretations or analytical commentary.\n\n'

         f'Reuse full paragraphs and sentences directly from the reference documents wherever possible. '
         f'Do not paraphrase, rewrite, or invent new content. Modify only variable details (such as building name, location, or component affected). \n\n'

         f'When assembling bullet points, select the same or most relevant ones from the reference document. '
         f'If uncertain, prefer to reuse rather than summarize.\n\n'

         f'SPECIAL INSTRUCTIONS FOR THIS SECTION:\n{section_instructions}\n\n'

         f'GENERAL NOTE: Keep the section concise, consistent with prior reports, '
         f'and based solely on reused text from the references. Do not generate new phrasing or elaboration.'


                


         )
        },
        {
            'role': 'user',
            'content': (
                f'REFERENCE DOCUMENTS:\n{context_text}\n\n'
                f'Focus only on the portion of the reference documents labeled or resembling the "{section_name.title()}" section. '
                f'Replicate its sentence structure and bullet formatting exactly.\n\n'
                f'USER REQUEST:\nGenerate the "{section_name.replace("_", " ").title()}" section for a damage assessment '
                f'report based on the following scenario: {query}\n\n'
                f'{section_name.replace("_", " ").title()} SECTION:'
            )
        }
   ]

    return prompt_messages


# ----------------------------
# Helper: generate OpenAI section content
# ----------------------------
def generate_section_content(section_name, query, collection, top_k=6):
    context_chunks = retrieve_context(collection, query, top_k=top_k)
    if not context_chunks:
        return f"Could not find relevant information for the {section_name.replace('_',' ')} section."

    prompt_messages = build_rag_prompt(query, context_chunks, section_name)

    if not openai.api_key:
        raise HTTPException(status_code=500, detail="OpenAI API key is not set. Set 'OPENAI_API_KEY' environment variable.")

    try:
        client = OpenAI(api_key=openai.api_key)
        resp = client.chat.completions.create(
            model='gpt-4.1',
            messages=prompt_messages,
            
            temperature=0.3
            
            #temperature=0
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"An error occurred during generation for {section_name.replace('_',' ')}: {e}"










# ----------------------------
# FastAPI Endpoint
# ----------------------------
@app.post("/read_fields")
async def read_fields(request: Request) -> JSONResponse:
    async with global_lock:
   

    # --- Attempt to parse JSON automatically ---
     parsed = None
    try:
        parsed = await request.json()
    except Exception:
        # Not valid JSON, treat as raw text
        body_bytes = await request.body()
        parsed = body_bytes.decode("utf-8", errors="replace").strip()

    # --- Store payload globally for later use ---
    global LAST_READ_FIELDS_PAYLOAD
    if isinstance(parsed, dict):
        LAST_READ_FIELDS_PAYLOAD = parsed
    elif isinstance(parsed, str):
        try:
            parsed_dict = json.loads(parsed)
            if isinstance(parsed_dict, dict):
                LAST_READ_FIELDS_PAYLOAD = parsed_dict
        except Exception:
            # Raw string, store as dict with single key
            LAST_READ_FIELDS_PAYLOAD = {"raw_text": parsed}
         


    fields = None
    prompt_override = None
    collection_name = "wie_reports"
    n_results = 5

    if isinstance(parsed, dict):
        # Case 1: JSON object
        fields = parsed.get("fields")
        prompt_override = parsed.get("prompt") or parsed.get("fields_text")
        collection_name = parsed.get("collection", collection_name)
        try:
            n_results = int(parsed.get("n_results", n_results))
        except Exception:
            pass
        # If dict has content but no fields/prompt, use the dict itself
        if not fields and not prompt_override and parsed:
            fields = parsed

    elif isinstance(parsed, str):
        # Case 2: JSON string or raw text
        try:
            # Try parsing string as JSON
            parsed_dict = json.loads(parsed)
            if isinstance(parsed_dict, dict):
                fields = parsed_dict.get("fields")
                prompt_override = parsed_dict.get("prompt") or parsed_dict.get("fields_text")
                collection_name = parsed_dict.get("collection", collection_name)
                try:
                    n_results = int(parsed_dict.get("n_results", n_results))
                except Exception:
                    pass
                if not fields and not prompt_override and parsed_dict:
                    fields = parsed_dict
            else:
                prompt_override = parsed
        except Exception:
            # Treat entire string as prompt
            prompt_override = parsed
    else:
        # Fallback for unexpected input type
        prompt_override = str(parsed)

    # --- Mask sensitive fields ---
    query_fields_for_chunks = fields if fields else {}
    sanitized_fields_for_gpt = mask_sensitive_fields(query_fields_for_chunks)

    # --- Build GPT query text ---
    if prompt_override:
        query_text_for_gpt = prompt_override
    elif isinstance(sanitized_fields_for_gpt, dict):
        query_text_for_gpt = _build_prompt_from_fields(sanitized_fields_for_gpt)
    else:
        query_text_for_gpt = str(sanitized_fields_for_gpt)

    client, collection = _get_vector_db_client_and_collection(collection_name)

    # Section-wise report generation
    report_sections_to_generate = [
        'purpose and objectives',
        'conclusions',
        'Background Information',
        'Inspection Observations',
        'Assessment',
        'recommendations for repairs',
        'references'
    ]

    generated_report_content = {}

    # Ensure folder exists for txt files
    output_dir = os.path.join(os.path.dirname(__file__), "generated_reports")
    os.makedirs(output_dir, exist_ok=True)

    for section_name in report_sections_to_generate:
        
        # Status message
        print(f"Generating response for section: {section_name.replace('_',' ')}...")

        # Generate GPT content
        section_content = generate_section_content(section_name, query_text_for_gpt, collection, top_k=n_results)
        generated_report_content[section_name] = section_content

        # Write each section to a separate .txt file
        section_filename = f"{section_name}.txt"
        section_path = os.path.join(output_dir, section_filename)
        with open(section_path, "w", encoding="utf-8") as f:
            f.write(section_content)

    
    
    print("=== Payload received in LAST_READ_FIELDS_PAYLOAD ===")
    for k, v in LAST_READ_FIELDS_PAYLOAD.items():
     print(f"{k}: {v}")

    
    
    subprocess.run(["python","filter.py"])
    maybe_trigger_pdf()
    trigger_page_generation()
    return JSONResponse(content={
        "query": query_text_for_gpt,
        "collection": collection_name,
        "n_results": n_results,
        "generated_report": generated_report_content,
        "message": "Responses are being generated and stored as separate text files per section."
    })


#####DBPUSH FEATURE#####


# ----------------------------
# Ensure spaCy model is available
# ----------------------------
MODEL_NAME = "en_core_web_sm"
try:
    if is_package(MODEL_NAME):
        nlp = spacy.load(MODEL_NAME)
    else:
        nlp = spacy.load(MODEL_NAME)
except OSError:
    print(f"Model '{MODEL_NAME}' not found. Downloading now...")
    subprocess.check_call([sys.executable, "-m", "spacy", "download", MODEL_NAME])
    nlp = spacy.load(MODEL_NAME)
print(f"spaCy model '{MODEL_NAME}' is ready.")

# ----------------------------
# Helper: Extract text from a single PDF
# ----------------------------
def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    full_text = []
    for page_num, page in enumerate(doc):
        text = page.get_text("text")
        full_text.append(f"\n\n=== PAGE {page_num+1} START ===\n{text.strip()}\n=== PAGE {page_num+1} END ===\n")
    doc.close()
    return "\n".join(full_text)

# ----------------------------
# Helper: Redact sensitive info from text
# ----------------------------
def redact_text(text):
    text = re.sub(r"\b[\w\.-]+@[\w\.-]+\.\w+\b", "[REDACTED_EMAIL]", text)
    text = re.sub(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b", "[REDACTED_PHONE]", text)
    text = re.sub(r"\b[A-Z]{1,3}[-]?\d{6,}\b", "[REDACTED_ID]", text)
    doc = nlp(text)
    redacted_text = text
    offset = 0
    for ent in doc.ents:
        if ent.label_ in ("PERSON", "ORG", "GPE", "LOC", "FAC"):
            start = ent.start_char + offset
            end = ent.end_char + offset
            replacement = f"[REDACTED_{ent.label_}]"
            redacted_text = redacted_text[:start] + replacement + redacted_text[end:]
            offset += len(replacement) - (end - start)
    return redacted_text

# ----------------------------
# Helper: Extract structured sections
# ----------------------------
def extract_sections(text):
    headers = [
        "purpose", "objectives", "site", "damage", "observation",
        "assessment", "finding", "conclusion", "recommendation", "reference"
    ]
    lines = text.splitlines()
    sections = {}
    current = "preamble"
    acc = []
    for line in lines:
        low = line.strip().lower()
        matched = None
        for h in headers:
            if low.startswith(h):
                matched = h
                break
        if matched:
            if acc:
                sections[current] = "\n".join(acc).strip()
            current = matched
            acc = []
        else:
            acc.append(line)
    if acc:
        sections[current] = "\n".join(acc).strip()
    # Normalize keys
    norm = {}
    for k, v in sections.items():
        if "purpose" in k or "objective" in k:
            key = "purpose_and_objectives"
        elif "site" in k:
            key = "site_description"
        elif "damage" in k:
            key = "damage_description"
        elif "observation" in k:
            key = "observations"
        elif "assessment" in k or "finding" in k:
            key = "assessment"
        elif "conclusion" in k:
            key = "conclusions"
        elif "recommendation" in k:
            key = "recommendations"
        elif "reference" in k:
            key = "references"
        else:
            key = k
        norm[key] = v
    return norm


# ----------------------------
# Endpoint: /db_push
# ----------------------------
@app.post("/db_push")
async def db_push(files: Optional[list[UploadFile]] = File(None)):
    async with global_lock:
    # ✅ If no files provided, skip DB push safely
     files = [f for f in (files or []) if f and getattr(f, "filename", None) not in (None, "")]
    if not files:
      return JSONResponse(content={
          "message": "No files provided. DB push skipped.",
           "reports": []
    })
      
     # Save file which is uploaded into output_template folder like with open 
    # Store file bytes for each upload so we only read once
    file_bytes_map = {}
    for uploaded_file in files:
        file_bytes = await uploaded_file.read()
        file_bytes_map[uploaded_file.filename] = file_bytes

    # Save file which is uploaded into output_template forlder like with open 

    base_dir = os.path.dirname(__file__)
    db_dir = os.path.join(base_dir, "vectordatabase")
    os.makedirs(db_dir, exist_ok=True)

    # Open existing collection or create if not present
    client = chromadb.PersistentClient(path=db_dir)
    collection_name = "wie_reports"
    try:
        collection = client.get_collection(collection_name, embedding_function=embedding_func)
    except:
        collection = client.create_collection(collection_name, embedding_function=embedding_func)

    processed_reports = []

    # Use a temporary directory for uploaded files
    with tempfile.TemporaryDirectory() as tmpdir:
        for uploaded_file in files:
            file_path = os.path.join(tmpdir, uploaded_file.filename)
            # Use the bytes we already read
            file_bytes = file_bytes_map.get(uploaded_file.filename, b"")
            with open(file_path, "wb") as f:
                f.write(file_bytes)

            pdf_paths = []
            # If ZIP, extract PDFs
            if uploaded_file.filename.lower().endswith(".zip"):
                with ZipFile(file_path, "r") as zip_ref:
                    zip_ref.extractall(tmpdir)
                pdf_paths.extend(glob.glob(os.path.join(tmpdir, "*.pdf")))
                pdf_paths.extend(glob.glob(os.path.join(tmpdir, "*.PDF")))
            elif uploaded_file.filename.lower().endswith((".pdf", ".PDF")):
                pdf_paths.append(file_path)
            else:
                continue  # Skip unsupported files

            for pdf_path in pdf_paths:
                try:
                    # Extract, redact, structure
                    text = extract_text_from_pdf(pdf_path)
                    redacted = redact_text(text)
                    sections = extract_sections(redacted)
                    report_id = os.path.basename(pdf_path).rsplit(".", 1)[0]
                    doc_json = {"report_id": report_id, "sections": sections}

                    # Add to collection
                    uid = str(uuid.uuid4())
                    collection.add(ids=[uid], documents=[json.dumps(doc_json)], metadatas=[{"report_id": report_id}])

                    processed_reports.append(report_id)
                except Exception as e:
                    print(f"Failed processing {pdf_path}: {e}")
            # Remove uploaded file
            os.remove(file_path)

    return JSONResponse(content={
        "message": f"Pushed {len(processed_reports)} report(s) to the DB.",
        "reports": processed_reports
    })


# === IMAGE STORAGE PATH CONFIG (Manually Editable) ===
BASE_UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
FRONT_IMAGE_DIR = os.path.join(BASE_UPLOAD_DIR, "front_image")
REFERENCE_IMAGE_DIR = os.path.join(BASE_UPLOAD_DIR, "reference_images")

# Ensure folders exist
os.makedirs(FRONT_IMAGE_DIR, exist_ok=True)
os.makedirs(REFERENCE_IMAGE_DIR, exist_ok=True)

# ----------------------------
# IMAGE UPLOAD FEATURE
# === IMAGE STORAGE PATH CONFIG (Manually Editable) ===
BASE_UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
FRONT_IMAGE_DIR = os.path.join(BASE_UPLOAD_DIR, "front_image")
REFERENCE_IMAGE_DIR = os.path.join(BASE_UPLOAD_DIR, "reference_images")

# Ensure folders exist
os.makedirs(FRONT_IMAGE_DIR, exist_ok=True)
os.makedirs(REFERENCE_IMAGE_DIR, exist_ok=True)






@app.post("/upload_images")
async def upload_images(
    front_image: Optional[UploadFile] = File(None),
    reference_images: Optional[List[UploadFile]] = File(None),
    front_caption: Optional[str] = Form(None),
    reference_captions: Optional[List[str]] = Form(None),
):
    async with global_lock:
     global LAST_UPLOADED_FRONT_IMAGE, LAST_UPLOADED_REFERENCE_IMAGES

    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    results = []

    # --- Clear old front images ---
    for f in os.listdir(FRONT_IMAGE_DIR):
        old_path = os.path.join(FRONT_IMAGE_DIR, f)
        if os.path.isfile(old_path):
            os.remove(old_path)
    LAST_UPLOADED_FRONT_IMAGE = ""

    # --- Clear old reference images ---
    for f in os.listdir(REFERENCE_IMAGE_DIR):
        old_path = os.path.join(REFERENCE_IMAGE_DIR, f)
        if os.path.isfile(old_path):
            os.remove(old_path)
    LAST_UPLOADED_REFERENCE_IMAGES = []

    # --- Process Front Image ---
    if front_image:
        front_path = os.path.join(FRONT_IMAGE_DIR, front_image.filename)
        with open(front_path, "wb") as buffer:
            shutil.copyfileobj(front_image.file, buffer)

        rewritten_caption = await rewrite_caption(front_caption, client)
        enhanced_caption = await enhance_caption(front_caption, client)

        results.append({
            "order": len(results) + 1,
            "type": "front",
            "filename": front_image.filename,
            "filepath": front_path,
            "original_caption": front_caption or None,
            "rewritten_caption": rewritten_caption,
            "enhanced_caption": enhanced_caption
        })

        LAST_UPLOADED_FRONT_IMAGE = front_path

    # --- Process Reference Images ---
    if reference_images:
        reference_images = [img for img in reference_images if img and getattr(img, "filename", None)]
        reference_captions = [c for c in (reference_captions or []) if c and c.strip()]

        for idx, img in enumerate(reference_images):
            ref_path = os.path.join(REFERENCE_IMAGE_DIR, img.filename)
            with open(ref_path, "wb") as buffer:
                shutil.copyfileobj(img.file, buffer)

            caption = reference_captions[idx] if reference_captions and idx < len(reference_captions) else None
            rewritten_caption = await rewrite_caption(caption, client)
            enhanced_caption = await enhance_caption(caption, client)

            results.append({
                "order": len(results) + 1,
                "type": "reference",
                "filename": img.filename,
                "filepath": ref_path,
                "original_caption": caption or None,
                "rewritten_caption": rewritten_caption,
                "enhanced_caption": enhanced_caption
            })

            LAST_UPLOADED_REFERENCE_IMAGES.append(ref_path)

    if not results:
         subprocess.run(["python", "merge_pdf.py"])
         return JSONResponse({
            "status": "no_action",
            "message": "No images or captions received. Nothing processed.",
            "images": []
        })

    # Save captions JSON
    captions_file = os.path.join(BASE_UPLOAD_DIR, "captions.json")
    with open(captions_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)

    # Trigger PDF generation if needed
    maybe_trigger_pdf()
    trigger_ref_generation()
    subprocess.run(["python","merge_pdf.py"])
    return JSONResponse({
        "status": "success",
        "message": f"Images and captions processed successfully. Captions saved at {captions_file}",
        "images": results
    })







# -----------------------
# Rewrite & Enhance Caption Helpers
async def rewrite_caption(caption: Optional[str], client) -> Optional[str]:
    if not caption or not caption.strip():
        return None
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert caption writer. Rewrite this caption clearly and professionally, with detail where necessary. Keep it within one line."},
                {"role": "user", "content": caption.strip()}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print("❌ Caption rewrite failed:", e)
        return None


async def enhance_caption(caption: Optional[str], client) -> Optional[str]:
    if not caption or not caption.strip():
        return None
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert caption writer. Enhance this caption professionally and clearly. Keep it within one line."},
                {"role": "user", "content": caption.strip()}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print("❌ Caption enhancement failed:", e)
        return None


@app.get("/download_final_report")
def download_final_report():
    pdf_path = final_pdf

    if not os.path.exists(pdf_path):
        return Response(content="PDF not found", status_code=404)

    with open(pdf_path, "rb") as f:
        pdf_data = f.read()

    return Response(
        content=pdf_data,
        media_type="application/pdf",
        headers={
            # ✅ allows Chrome/Firefox inline PDF rendering
            "Content-Disposition": "inline; filename=final_report.pdf",

            # ✅ CORS + embedding fixes
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Range",
            "Access-Control-Expose-Headers": "Content-Range",
            "Accept-Ranges": "bytes",
            "Cross-Origin-Resource-Policy": "cross-origin",
            "X-Frame-Options": "ALLOWALL",
            # Firefox-specific fixes
            "Cross-Origin-Embedder-Policy": "unsafe-none",
            "Cross-Origin-Opener-Policy": "unsafe-none",
            # ✅ disables caching
            "Cache-Control": "no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )

DB_PATH = os.path.join(os.path.dirname(__file__), "users.db")

# User model for API
class User(BaseModel):
    username: str
    password: str
    role: str = "normal"  # "admin" or "normal"

# DB init helper
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'normal'))
        )
    """)
    conn.commit()
    conn.close()

init_db()

# Helper: get user by username
def get_user(username):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, username, password, role FROM users WHERE username=?", (username,))
    row = c.fetchone()
    conn.close()
    if row:
        return {"id": row[0], "username": row[1], "password": row[2], "role": row[3]}
    return None

# Endpoint: login
@app.post("/login")
async def login(user: User):
    db_user = get_user(user.username)
    if not db_user:
        return JSONResponse(status_code=404, content={"detail": "User not found"})
    if db_user["password"] != user.password:
        return JSONResponse(status_code=401, content={"detail": "Incorrect password"})
    return JSONResponse(content={
        "message": "Login successful",
        "user": {"username": db_user["username"], "role": db_user["role"]}
    })

# Endpoint: add user
@app.post("/add_user")
async def add_user(user: User):
    if get_user(user.username):
        return JSONResponse(status_code=400, content={"detail": "User already exists"})
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", (user.username, user.password, user.role))
    conn.commit()
    conn.close()
    return JSONResponse(content={"message": "User added successfully"})

# Endpoint: update user
@app.put("/update_user/{username}")
async def update_user(username: str, user: User):
    if not get_user(username):
        return JSONResponse(status_code=404, content={"detail": "User not found"})
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET password=?, role=? WHERE username=?", (user.password, user.role, username))
    conn.commit()
    conn.close()
    return JSONResponse(content={"message": "User updated successfully"})

# Endpoint: delete user
@app.delete("/delete_user/{username}")
async def delete_user(username: str):
    if not get_user(username):
        return JSONResponse(status_code=404, content={"detail": "User not found"})
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE username=?", (username,))
    conn.commit()
    conn.close()
    return JSONResponse(content={"message": "User deleted successfully"})

# Endpoint: fetch all users
@app.get("/users")
async def fetch_users():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT username, role FROM users")
    rows = c.fetchall()
    conn.close()
    users = [{"username": r[0], "role": r[1]} for r in rows]
    return JSONResponse(content={"users": users})


def airtable_get(url, params=None):
    headers = {"Authorization": f"Bearer {AIRTABLE_TOKEN}"}
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print("❌ Error:", response.status_code, response.text)
        return None


@app.post("/report_fields")
async def report_fields(request: Request):
    # Accept any JSON/text input (for future use)
    try:
        data = await request.json()
        search_value = (
            data.get("record_name")
            or data.get("wie_file_number")
            or data.get("file_number")
            or ""
        ).strip()
    except Exception:
        data = await request.body()
        search_value = data.decode("utf-8", errors="replace").strip()

    if not search_value:
        return JSONResponse(content={"error": "Missing record_name in request."}, status_code=400)

    # Convert to uppercase (case insensitive search)
    search_value = search_value.upper()

    # === Fetch main record ===
    url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_ID}"
    params = {
        "view": VIEW_ID,
        "filterByFormula": f"{{Name}} = '{search_value}'"
    }
    data = airtable_get(url, params)

    if not data or "records" not in data or not data["records"]:
        return JSONResponse(content={"error": f"No record found for Name = '{search_value}'."}, status_code=404)

    record = data["records"][0]["fields"]

    # Extract fields
    first_name = record.get("First Name", "")
    last_name = record.get("Last Name", "")
    full_name = f"{first_name} {last_name}".strip()
    location = record.get("Location", "N/A")
    email = record.get("Auto Client Email", "N/A")
    claim_id = record.get("Client/Claim ID", "N/A")
    dol = record.get("DOL", "N/A")
    final_date = record.get("Final Sent", "N/A")

    # ✅ Clean email output
    if isinstance(email, list):
        email = ", ".join(email)

    # === Handle linked Client field ===
    client_field = record.get("Client", [])
    client_name = "N/A"
    client_contact_name = "N/A"
    if isinstance(client_field, list) and client_field:
        client_id = client_field[0]  # take first linked record
        client_url = f"https://api.airtable.com/v0/{BASE_ID}/{CLIENT_TABLE_ID}/{client_id}"
        client_data = airtable_get(client_url)
        if client_data and "fields" in client_data:
            client_full = client_data["fields"].get("Name", "N/A")
            # Split the client name if dash exists
            if " - " in client_full:
                parts = client_full.split(" - ", 1)
                client_name = parts[0].strip()
                contact_part = parts[1].strip()
                # Reverse name order if it's like "Last, First"
                if "," in contact_part:
                    last, first = [x.strip() for x in contact_part.split(",", 1)]
                    client_contact_name = f"{first} {last}"
                else:
                    client_contact_name = contact_part
            else:
                client_name = client_full

    # === Format Dates ===
    formatted_dol = dol
    try:
        if isinstance(dol, str):
            dol_clean = dol.split("T")[0] if "T" in dol else dol
            if len(dol_clean) == 10 and dol_clean[4] == "-":
                formatted_dol = datetime.strptime(dol_clean, "%Y-%m-%d").strftime("%m-%d-%Y")
    except Exception as e:
        print("DOL format error:", e)

    formatted_report_date = final_date
    try:
        if isinstance(final_date, str):
            final_clean = final_date.split("T")[0] if "T" in final_date else final_date
            if len(final_clean) == 10 and final_clean[4] == "-":
                formatted_report_date = datetime.strptime(final_clean, "%Y-%m-%d").strftime("%B %d, %Y")
    except Exception as e:
        print("Report date format error:", e)

    print("Formatted Report Date:", formatted_report_date)
    print("Formatted DOL:", formatted_dol)

    # === Construct JSON response ===
    fields = {
        "insured_name": full_name,
        "insured_address": location,
        "client_contact_email": email,
        "claim_number": claim_id,
        "client_name": client_name,
        "client_contact_name": client_contact_name,
        "date_of_loss": formatted_dol,
        "report_date": formatted_report_date
    }

    return JSONResponse(content={"header": fields})
