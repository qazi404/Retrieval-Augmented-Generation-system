🧠 AI Models Used

OpenAI GPT Models

gpt-4.1 → Generates detailed technical report sections (e.g., Purpose and Objectives, Assessment, Conclusions, etc.) using RAG (Retrieval-Augmented Generation).

gpt-4o-mini → Used for caption rewriting and enhancement in the image upload feature.

Both models are accessed via:

from openai import OpenAI
client = OpenAI(api_key=openai.api_key)


Sentence Transformer Model

Model: all-mpnet-base-v2

Used to generate embeddings for documents stored in the ChromaDB vector database.

Implemented via:

from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
embedding_func = SentenceTransformerEmbeddingFunction(model_name="all-mpnet-base-v2")


spaCy Model

Model: en_core_web_sm

Used for Named Entity Recognition (NER) to redact sensitive data like names, organizations, and locations in uploaded PDFs.

If not installed, it auto-downloads and loads dynamically.

⚙️ Frameworks and Libraries

Category	Tool	Purpose
Backend Framework	FastAPI	API endpoints for reading fields, uploading images, pushing to DB, report generation, etc.
Middleware	CORS Middleware	Allows cross-origin requests for web integration.
Database (Vector)	ChromaDB (PersistentClient)	Stores and retrieves report embeddings for RAG-based context retrieval.
AI/ML	OpenAI API + SentenceTransformer + spaCy	GPT for content generation, sentence transformer for vector embeddings, spaCy for text redaction.
PDF Handling	PyMuPDF (fitz)	Extracts text from uploaded PDF files.
File Compression	ZipFile	Extracts multiple PDFs from uploaded ZIPs.
Database (Relational)	SQLite3	Manages user accounts and roles for login/authentication.
Environment Management	dotenv	Loads API keys and Airtable credentials.
HTTP Requests	requests	Connects to Airtable API to fetch records.

🧩 Core AI-Powered Workflows
1. RAG-Based Report Generation

Vector DB: ChromaDB collection → wie_reports

Embedding model: all-mpnet-base-v2

Retrieval: Fetches relevant documents (by query) for context.

Generation: Sends context + user query → GPT-4.1

Output: Generates sections like:

Purpose and Objectives

Background Information

Inspection Observations

Assessment

Conclusions

Recommendations for Repairs

References

Each section is saved as a .txt file in /generated_reports.

2. AI Caption Processing

When uploading images:

GPT-4o-mini rewrites and enhances image captions for clarity and professionalism.

Results stored as JSON in /uploads/captions.json.

3. PDF Generation

Combines:

Extracted fields

Uploaded images

AI-generated content

Generates final report PDFs using a local template via front_template.render_pdf() and scripts (content_templating.py, template_ref.py, merge_pdf.py).

4. Data Redaction & Processing

Uses spaCy NER to redact:

Names (PERSON)

Organizations (ORG)

Locations (GPE/LOC/FAC)

Also redacts emails, phone numbers, and IDs with regex before pushing to ChromaDB.

5. Airtable Integration

Pulls claim and client data:

Uses environment vars: AIRTABLE_TOKEN, BASE_ID, TABLE_ID, CLIENT_TABLE_ID, etc.

Retrieves and formats insured details for report headers.

🗂️ Database Architecture

SQLite (users.db)

Tables: users

Columns: id, username, password, role

Role-based system: admin or normal

ChromaDB (vectordatabase/)

Stores:

JSON-formatted report sections

Embeddings using SentenceTransformer

Metadata: report_id, section

🧾 FastAPI Endpoints Overview

Endpoint	Function
/read_fields	Generates report sections using GPT-4.1 (RAG-based).
/db_push	Uploads PDFs/ZIPs → extracts text → redacts → pushes to ChromaDB.
/upload_images	Uploads images + captions → rewrites captions using GPT-4o-mini → regenerates report.
/download_final_report	Returns the merged final report PDF.
/login, /add_user, /update_user, /delete_user, /users	User authentication & management APIs.
/report_fields	Fetches claim/client data from Airtable API.

🧮 Key AI Model Summary
Model	Type	Use Case
gpt-4.1	LLM	Generate professional engineering report sections
gpt-4o-mini	LLM	Caption rewriting/enhancement
all-mpnet-base-v2	Embedding model	Text vectorization for RAG search
en_core_web_sm	NLP model	Text redaction using NER