# MemoLedger (মেমোলেজার)

> **Next-Generation AI Invoice Extraction, Handwritten Memo Digitization & Append-Only Inventory Ledger**  
> *Built for fast-moving wholesale and retail supply chain hubs in Bangladesh and emerging markets.*

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16%20%7C%20pgvector-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://www.docker.com)
[![Architecture](https://img.shields.io/badge/Architecture-Append--Only%20Ledger-0D9488)](#architecture)
[![License](https://img.shields.io/badge/License-Proprietary-slate)](LICENSE)

---

## 1. Executive Summary: The "Reverse Process"

In traditional wholesale and retail distribution hubs (such as Chawkbazar, Moulvibazar, Khatunganj, Islampur, and Karwan Bazar), business moves at lightning speed. Suppliers and merchants write rapid handwritten cash memos (চালান / মেমো) on carbon-copy paper slips using abbreviations, mixed Bengali-English numerals, and informal short codes (e.g., `Lilac B/C`, `Soft (f)`, `BG N/Strip - 20P x 18 = 360`).

### Why Traditional ERPs & POS Fail
Traditional retail software forces business owners to alter their behavior:
- Sit at a desktop terminal or type on a keyboard.
- Scan barcodes that wholesale boxes often lack.
- Hire dedicated computer operators.

### How MemoLedger Inverts the Paradigm
**MemoLedger implements the "Reverse Process"**:
1. **Zero Habit Change**: Merchants continue writing paper slips just as they have for decades.
2. **Instant Capture**: A single smartphone photo turns that paper slip into digital ledger entries in under 3 seconds.
3. **Automated Discrepancy Detection**: Checks row-by-row arithmetic (`qty × price = line total`) against the written total to stop overpayments immediately.
4. **Instant Multi-Channel Output**: Automatically generates inventory stock adjustments, supplier debt ledgers, and client-ready WhatsApp/PDF invoices.

---

## 2. Core Business Features

| Category | Capability | Description |
| :--- | :--- | :--- |
| **OCR & Extraction** | **Bilingual Handwritten OCR** | Detects English & Bengali numerals (`১`, `২`, `৩` $\to$ `1`, `2`, `3`), parenthesized shades/sizes (`(SH)`, `(928)`, `(13)`, `(F)`), and shorthand item names. |
| **Catalog Intelligence** | **Full Name & Short Name Mapping** | Dynamically resolves ambiguous handwritten tokens (e.g., `Lilac B/C` $\rightarrow$ *Lilac Brightening Cream*, `YC-Cu F/W` $\rightarrow$ *YC Cucumber Face Wash*). |
| **Deduplication** | **1-to-1 Row Correspondence** | Prevents repeated product matching across rows. If handwriting is unreadable, product name is left blank (`""`) while preserving detected rates and quantities. |
| **Verification** | **Both-End Total Reconciliation** | Compares the live calculated subtotal (`∑ qty × rate`) with the image's written total in an editable field. Instantly flags math errors before commitment. |
| **Inventory Control** | **Append-Only Stock Ledger** | Every approved line posts an immutable `PURCHASE_RECEIPT` movement with running balance tracking, audit metadata, and cost price history. |
| **Risk Prevention** | **Duplicate Memo Shield** | Cryptographic SHA-256 image hashing blocks accidental duplicate memo submissions and double payments. |
| **Volatility Tracking** | **Supplier Price History** | Tracks historic purchase rates per supplier and flags price spikes exceeding normal thresholds. |
| **Client Output** | **One-Tap WhatsApp & PDF Invoicing** | Renders professional bilingual PDF invoices (Noto Sans Bengali) and opens click-to-chat WhatsApp messages with formatted order summaries. |
| **User Interface** | **Touch-Optimized Desktop & Mobile UI** | Split-screen workspace with interactive bounding box overlays on the memo photo and widened input fields for comfortable manual editing. |
| **Business Intelligence** | **Guarded Natural Language BI** | "Ask Data" interface translates plain text business questions (*"What was my total purchase from K Color this week?"*) into safe, read-only SQL queries. |

---

## 3. Architecture & Data Flow

```mermaid
flowchart TD
    subgraph Capture["1. Capture & Input Layer"]
        Camera["Mobile Camera / Desktop Upload"]
        Crop["Canvas Perspective Crop & Deskew"]
        Manual["Manual Line Form Entry"]
    end

    subgraph Pipeline["2. Memo Extraction Engine"]
        StageA["Stage A: Verbatim OCR & Bounding Box Detection"]
        StageB["Stage B: Layout-Agnostic Equation Parsing"]
        Norm["Normalization: Bengali Digits, Units & Shorthand"]
        Resolver["Hybrid Product Resolver: Short Name + Vector Embeddings"]
        Reconcile["Both-End Reconciliation: Lines Sum vs. Image Written Total"]
    end

    subgraph Review["3. Synchronized Review Workspace"]
        PhotoView["Interactive Photo Canvas with SVG BBox Highlights"]
        FormTable["Widened Editable Table: Name, Qty, Rate, Total"]
        TotalFoot["Live Subtotal vs. Editable Image Total Indicator"]
    end

    subgraph Ledger["4. Ledger & Fulfillment Core"]
        Commit["One-Tap Approval & Ledger Commit"]
        Stock["Append-Only Stock Movements (PURCHASE_RECEIPT)"]
        PriceHist["Supplier Price History & Audit Log"]
        PDFGen["Bilingual PDF Generator (WeasyPrint)"]
        WhatsApp["WhatsApp 1-Click Invoice Share"]
    end

    Camera --> Crop --> StageA
    Manual --> FormTable
    Crop --> StageA --> StageB --> Norm --> Resolver --> Reconcile
    Reconcile --> PhotoView <--> FormTable
    FormTable --> TotalFoot --> Commit
    Commit --> Stock
    Commit --> PriceHist
    Commit --> PDFGen
    Commit --> WhatsApp
```

---

## 4. Technical Architecture

| Layer | Technologies |
| :--- | :--- |
| **Backend Framework** | **Python 3.12**, **FastAPI**, **Pydantic v2**, **SQLAlchemy 2.0 (ORM)** |
| **Database & Search** | **PostgreSQL 16** with `pgvector` (vector embeddings) and `pg_trgm` (trigram fuzzy matching) |
| **OCR & Vision** | **RapidOCR (ONNX)** local engine with fallback support for **Google Gemini 2.0 / 1.5 Flash Vision API** |
| **Asynchronous Engine** | **Celery** with **Redis 7** broker for background image processing and telemetry |
| **Object Storage** | S3-Compatible Storage (**MinIO** for local/on-premise, AWS S3 / Cloudflare R2 for production) |
| **Frontend Architecture** | **Jinja2 SSR**, **Tailwind CSS**, **Vanilla JavaScript (ES Modules)**, **SVG Canvas Overlay** |
| **Document Generation** | **WeasyPrint** (Bilingual PDF with Noto Sans Bengali font), **OpenPyXL** (Excel export) |
| **Security & Guardrails** | AST-validated SQL query executor, JWT authentication, tenant-scoped data isolation |

---

## 5. Directory Structure

```
invoice-maker/
├── app/
│   ├── api/v1/                # REST API Endpoints (Auth, Memos, Products, Stock, Reports)
│   ├── core/                  # Database session, app settings, JWT security
│   ├── models/                # SQLAlchemy models (Tenant, User, Supplier, Product, Memo, Stock)
│   ├── schemas/               # Pydantic v2 validation and response schemas
│   ├── services/
│   │   ├── extraction/        # Vision OCR, normalizer, arithmetic reconciler, pipeline
│   │   ├── matching/          # Hybrid resolver, multilingual vector embedder (pgvector)
│   │   ├── ledger/            # Stock movement service, price history, anomaly detection
│   │   ├── bi/                # Guarded Text-to-SQL conversational query engine
│   │   └── storage/           # S3 / MinIO object storage service
│   ├── static/                # Compiled Tailwind CSS, JavaScript modules
│   └── templates/             # Jinja2 responsive templates (review, upload, stock, products)
├── data/                      # Local storage and sample test image assets
├── evaluation/                # Synthetic memo generator, golden dataset, benchmark runner
├── scripts/
│   ├── seed_data.py           # Production deployment database initialization script
│   ├── clear_upload_data.py   # Resets upload memos while preserving product catalog
│   ├── run_tests.py           # Complete unit and integration test suite
│   ├── run_crud_tests.py      # Memo and line-item CRUD lifecycle tests
│   └── test_product_crud_and_bulk.py # Product database and short-name bulk import tests
├── docker-compose.yml         # Container orchestration (App, PostgreSQL 16, Redis)
├── Dockerfile                 # Multi-stage production container build
├── pyproject.toml             # Project dependency specification
└── README.md                  # Project documentation
```

---

## 6. Getting Started

### Prerequisites
- [Docker](https://docs.docker.com/get-docker/) & [Docker Compose](https://docs.docker.com/compose/)
- Alternatively: Python 3.12+ and PostgreSQL 16 with `pgvector` extension

### 1. Configure Environment
Create your environment configuration:
```bash
cp .env.example .env
```

Key environment configurations in `.env`:
```ini
ENVIRONMENT=development
DEBUG=True
SECRET_KEY=your-secure-secret-key

DATABASE_URL=postgresql://postgres:password@localhost:5433/memoledger
REDIS_URL=redis://localhost:6380/0

VISION_LLM_PROVIDER=mock   # or 'gemini'
GEMINI_API_KEY=            # Required if using Gemini Vision API
```

### 2. Start Services via Docker Compose
```bash
docker compose up -d
```
This automatically provisions:
- **`memoledger_postgres`**: PostgreSQL 16 on port `5433` (configured with `pgvector` & `pg_trgm`)
- **`memoledger_redis`**: Redis 7 cache & queue on port `6380`
- **`memoledger_app`**: FastAPI web server on port `8000`

### 3. Initialize Database & Seed Canonical Products
Run the deployment seeder to populate canonical products, short names, suppliers, and embeddings:
```bash
docker exec -e PYTHONPATH=/app memoledger_app python scripts/seed_data.py
```

### 4. Access the Application
- **Web Application**: [http://localhost:8000](http://localhost:8000)
- **Interactive OpenAPI Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Default Owner Credentials**:
  - Email: `owner@dhakacosmetics.com`
  - Password: `admin123`

---

## 7. Verification & Automated Testing

MemoLedger includes a comprehensive automated test suite covering normalizers, arithmetic reconciliation, fuzzy matching, stock movements, and text-to-SQL security.

### Run All Test Suites
```bash
# 1. Core Verification Suite (16 Tests)
docker exec -e PYTHONPATH=/app memoledger_app python scripts/run_tests.py

# 2. Memo & Line CRUD Operations Suite (4 Tests)
docker exec -e PYTHONPATH=/app memoledger_app python scripts/run_crud_tests.py

# 3. Product Database & Bulk Import Suite (4 Tests)
docker exec -e PYTHONPATH=/app memoledger_app python scripts/test_product_crud_and_bulk.py
```

### Resetting Upload Data
To clear uploaded memos, lines, and stock movements for a fresh upload session while preserving the complete product catalog:
```bash
docker exec -e PYTHONPATH=/app memoledger_app python scripts/clear_upload_data.py
```

---

## 8. Canonical Product Catalog Reference

The default seed file includes standard cosmetics and personal care products matched against authentic wholesale memos:

| Official Full Product Name | Short Name (Receipt Shorthand) | Brand | Category | Cost Price |
| :--- | :--- | :--- | :--- | :--- |
| **Lilac Brightening Cream** | `Lilac B/C` | Lilac | Face Cream | ৳600.00 |
| **Zafran Hair Growth Therapy** | `Zafran H/Oil` | Zafran | Hair Oil | ৳220.00 |
| **Bath Salt** | `Bath Salt` | Bath Care | Body Care | ৳150.00 |
| **Soft Finish Sun Milk** | `Soft (f)` | Missha | Sun Care | ৳250.00 |
| **YC Cucumber Face Wash** | `YC-Cu F/W` | YC | Face Wash | ৳145.00 |
| **SASI BB Perfect Powder** | `Sasi BB - Powder` | SASI | Loose Powder | ৳220.00 |
| **Sunscreen Cream 625ml** | `Sun 625ml (SH)` | Sun | Skin Care | ৳1050.00 |
| **Emeli Matte Lipstick** | `Emeli Lip (928)` | Emeli | Lip Makeup | ৳140.00 |
| **W7 Eye Shadow Palette** | `W7 Eye` | W7 | Eye Makeup | ৳200.00 |
| **BOB Long Lash Mascara** | `BOB: Mas (13)` | BOB | Eye Makeup | ৳210.00 |
| **Vaseline Jelly Cocoa Butter** | `Vase 50ml (J) Co` | Vaseline | Skin Care | ৳150.00 |
| **Ribana Organic Castor Oil** | `Ribana Castor oil` | Ribana | Hair & Skin Oil | ৳550.00 |
| **Cosrx Salicylic Acid Gentle Cleanser** | `Cosrx Sali (F)` | Cosrx | Facial Cleanser | ৳900.00 |
| **Bioaqua Nose Blackhead Strip** | `BG N/Strip` | Bioaqua | Nose Strip | ৳18.00 |
| **Kojic Acid Rice Face Wash** | `Koj-Rice (F)` | Kojic | Face Wash | ৳750.00 |
| **Dabo All In One Cream** | `Dabo. All in 1 (e)` | Dabo | Face Cream | ৳800.00 |
| **Kado 160g Face Wash Powder** | `Kado 160g pawd` | Kado | Powder Cleanser | ৳280.00 |
| **Mango Hair Removal Wax** | `Mango Wax` | Mango | Hair Removal | ৳300.00 |
| **Wax Strips Paper** | `Wax Paper (s)` | Generic | Wax Paper | ৳70.00 |

---

## 9. API Reference Overview

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/v1/auth/login` | `POST` | Authenticates user and issues JWT bearer token. |
| `/api/v1/memos/upload` | `POST` | Uploads memo photo, computes image hash, and enqueues extraction pipeline. |
| `/api/v1/memos/{id}` | `GET` | Fetches memo metadata, extracted lines, status, and discrepancy flags. |
| `/api/v1/memos/{id}/lines` | `PUT` | Saves draft updates to line items, prices, quantities, and memo total amount. |
| `/api/v1/memos/{id}/commit` | `POST` | Approves memo, locks modifications, and posts movements to stock ledger. |
| `/api/v1/memos/{id}/pdf` | `GET` | Generates bilingual print-ready PDF invoice. |
| `/api/v1/products` | `GET / POST` | Lists and creates catalog products with full name and short name. |
| `/api/v1/products/bulk` | `POST` | Bulk imports products using `Full Name - Short Name` syntax. |
| `/api/v1/stock` | `GET` | Returns real-time variant stock balances and recent ledger movements. |
| `/api/v1/ask-data` | `POST` | Natural language business queries translated into secure read-only SQL. |

---

## 10. License

Proprietary — All rights reserved. Built for retail and wholesale supply chain automation.
