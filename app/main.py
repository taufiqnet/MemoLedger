import os
import json
import uuid
from typing import Optional
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.config import settings
from app.core.database import get_db, Base, engine
from app.api.deps import get_current_user, get_current_tenant
from app.models.user import User
from app.models.tenant import Tenant
from app.models.memo import Memo
from app.models.product import Product, ProductVariant
from app.models.supplier import Supplier
from app.models.stock import StockMovement

from app.api.v1.auth import router as auth_router
from app.api.v1.memos import router as memos_router
from app.api.v1.products import router as products_router
from app.api.v1.suppliers import router as suppliers_router
from app.api.v1.stock import router as stock_router
from app.api.v1.reports import router as reports_router
from app.api.v1.ask_data import router as ask_data_router

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="MemoLedger API",
    description="Mobile-first memo extraction, stock ledger, and invoice generator for Bangladeshi businesses",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

templates_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=templates_dir)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(memos_router, prefix="/api/v1")
app.include_router(products_router, prefix="/api/v1")
app.include_router(suppliers_router, prefix="/api/v1")
app.include_router(stock_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
app.include_router(ask_data_router, prefix="/api/v1")


@app.get("/", response_class=HTMLResponse)
def root():
    return RedirectResponse(url="/dashboard")


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    memos = db.query(Memo).filter(
        Memo.tenant_id == tenant.id
    ).order_by(desc(Memo.created_at)).limit(10).all()

    total_memos = db.query(Memo).filter(Memo.tenant_id == tenant.id).count()
    pending_review = db.query(Memo).filter(Memo.tenant_id == tenant.id, Memo.status == "REVIEW_REQUIRED").count()
    
    approved_memos = db.query(Memo).filter(Memo.tenant_id == tenant.id, Memo.status == "APPROVED").all()
    total_spent = sum(float(m.extracted_total or 0) for m in approved_memos)

    variants = db.query(ProductVariant).join(Product).filter(Product.tenant_id == tenant.id).all()
    low_stock_count = sum(1 for v in variants if v.current_stock <= 5)

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "user": current_user,
            "tenant": tenant,
            "memos": memos,
            "total_memos": total_memos,
            "pending_review": pending_review,
            "total_spent": total_spent,
            "low_stock_count": low_stock_count,
        }
    )


@app.get("/upload", response_class=HTMLResponse)
def upload_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    suppliers = db.query(Supplier).filter(Supplier.tenant_id == tenant.id).all()
    variants = db.query(ProductVariant).join(Product).filter(Product.tenant_id == tenant.id).all()
    recent_memos = db.query(Memo).filter(Memo.tenant_id == tenant.id).order_by(desc(Memo.created_at)).limit(5).all()
    return templates.TemplateResponse(
        request=request,
        name="upload.html",
        context={
            "user": current_user,
            "tenant": tenant,
            "suppliers": suppliers,
            "variants": variants,
            "recent_memos": recent_memos,
        }
    )


@app.get("/review/{memo_id}", response_class=HTMLResponse)
def review_page(
    request: Request,
    memo_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    memo = db.query(Memo).filter(
        Memo.id == memo_id,
        Memo.tenant_id == tenant.id
    ).first()
    if not memo:
        raise HTTPException(status_code=404, detail="Memo not found")

    variants = db.query(ProductVariant).join(Product).filter(Product.tenant_id == tenant.id).all()

    lines_data = [
        {
            "id": str(l.id),
            "line_number": l.line_number,
            "bbox": l.bbox,
            "raw_text": l.raw_text,
            "parsed_name": l.parsed_name,
            "parsed_variant": l.parsed_variant,
            "parsed_qty": float(l.parsed_qty),
            "parsed_unit": l.parsed_unit,
            "parsed_unit_price": float(l.parsed_unit_price or 0),
            "parsed_line_total": float(l.parsed_line_total or 0),
            "matched_variant_id": str(l.matched_variant_id) if l.matched_variant_id else None,
            "status": l.status,
            "anomaly_flags": l.anomaly_flags or [],
        }
        for l in memo.lines
    ]

    return templates.TemplateResponse(
        request=request,
        name="review.html",
        context={
            "user": current_user,
            "tenant": tenant,
            "memo": memo,
            "variants": variants,
            "lines_json": json.dumps(lines_data),
        }
    )


@app.get("/stock", response_class=HTMLResponse)
def stock_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    variants = db.query(ProductVariant).join(Product).filter(Product.tenant_id == tenant.id).all()
    movements = db.query(StockMovement).filter(
        StockMovement.tenant_id == tenant.id
    ).order_by(desc(StockMovement.created_at)).limit(50).all()

    return templates.TemplateResponse(
        request=request,
        name="stock.html",
        context={
            "user": current_user,
            "tenant": tenant,
            "variants": variants,
            "movements": movements,
        }
    )


@app.get("/products", response_class=HTMLResponse)
def products_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    products = db.query(Product).filter(Product.tenant_id == tenant.id).all()
    return templates.TemplateResponse(
        request=request,
        name="products.html",
        context={
            "user": current_user,
            "tenant": tenant,
            "products": products,
        }
    )


@app.get("/suppliers", response_class=HTMLResponse)
def suppliers_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    suppliers = db.query(Supplier).filter(Supplier.tenant_id == tenant.id).all()
    return templates.TemplateResponse(
        request=request,
        name="suppliers.html",
        context={
            "user": current_user,
            "tenant": tenant,
            "suppliers": suppliers,
        }
    )


@app.get("/ask-data", response_class=HTMLResponse)
def ask_data_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
):
    return templates.TemplateResponse(
        request=request,
        name="ask_data.html",
        context={
            "user": current_user,
            "tenant": tenant,
        }
    )
