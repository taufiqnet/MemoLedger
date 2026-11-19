import io
from decimal import Decimal
from typing import Optional
from jinja2 import Template
from app.models.memo import Memo

HTML_INVOICE_TEMPLATE = """
<!DOCTYPE html>
<html lang="bn">
<head>
<meta charset="UTF-8">
<style>
  @page {
    size: A4;
    margin: 1.5cm;
  }
  body {
    font-family: 'Noto Sans Bengali', 'DejaVu Sans', sans-serif;
    color: #1e293b;
    font-size: 13px;
    line-height: 1.5;
  }
  .header {
    border-bottom: 2px solid #0f766e;
    padding-bottom: 12px;
    margin-bottom: 20px;
    display: flex;
    justify-content: space-between;
  }
  .title {
    font-size: 24px;
    font-weight: bold;
    color: #0f766e;
  }
  .subtitle {
    font-size: 13px;
    color: #64748b;
  }
  .meta-table {
    width: 100%;
    margin-bottom: 25px;
  }
  .meta-table td {
    padding: 4px 0;
  }
  .items-table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 20px;
  }
  .items-table th {
    background-color: #f1f5f9;
    color: #334155;
    text-align: left;
    padding: 8px;
    border-bottom: 2px solid #cbd5e1;
    font-size: 12px;
    text-transform: uppercase;
  }
  .items-table td {
    padding: 8px;
    border-bottom: 1px solid #e2e8f0;
  }
  .text-right {
    text-align: right;
  }
  .total-card {
    float: right;
    width: 250px;
    margin-top: 10px;
  }
  .total-row {
    display: flex;
    justify-content: space-between;
    padding: 6px 0;
  }
  .grand-total {
    border-top: 2px solid #0f766e;
    font-size: 16px;
    font-weight: bold;
    color: #0f766e;
  }
  .footer {
    margin-top: 80px;
    text-align: center;
    font-size: 11px;
    color: #94a3b8;
    border-top: 1px solid #e2e8f0;
    padding-top: 10px;
  }
</style>
</head>
<body>

<div class="header">
  <div>
    <div class="title">{{ tenant_name }}</div>
    <div class="subtitle">স্মার্ট ইনভয়েস ও ক্যাশ মেমো (Smart Invoice & Memo)</div>
  </div>
  <div style="text-align: right;">
    <div style="font-weight: bold; font-size: 15px;">মেমো নং: {{ memo.memo_number or 'N/A' }}</div>
    <div style="color: #64748b;">তারিখ: {{ memo.memo_date or 'N/A' }}</div>
  </div>
</div>

<table class="meta-table">
  <tr>
    <td style="width: 50%;">
      <strong>সরবরাহকারী (Supplier):</strong><br>
      {{ supplier_name or 'সাধারণ সরবরাহকারী' }}<br>
      {{ supplier_phone or '' }}
    </td>
    <td style="width: 50%; text-align: right;">
      <strong>স্ট্যাটাস:</strong> 
      <span style="color: #047857; font-weight: bold;">অনুমোদিত (APPROVED)</span><br>
      <strong>জেনারেট সময়:</strong> {{ current_date }}
    </td>
  </tr>
</table>

<table class="items-table">
  <thead>
    <tr>
      <th style="width: 5%;">নং</th>
      <th style="width: 45%;">বিবরণ (Item & Variant)</th>
      <th class="text-right" style="width: 15%;">পরিমাণ (Qty)</th>
      <th class="text-right" style="width: 15%;">দর (Rate ৳)</th>
      <th class="text-right" style="width: 20%;">মোট (Total ৳)</th>
    </tr>
  </thead>
  <tbody>
    {% for line in memo.lines %}
    <tr>
      <td>{{ line.line_number }}</td>
      <td>
        <strong>{{ line.parsed_name or line.raw_text }}</strong>
        {% if line.parsed_variant %}<span style="color: #64748b;"> ({{ line.parsed_variant }})</span>{% endif %}
      </td>
      <td class="text-right">{{ line.parsed_qty }} {{ line.parsed_unit }}</td>
      <td class="text-right">৳{{ "%.2f"|format(line.parsed_unit_price or 0) }}</td>
      <td class="text-right">৳{{ "%.2f"|format(line.parsed_line_total or 0) }}</td>
    </tr>
    {% endfor %}
  </tbody>
</table>

<div class="total-card">
  <table style="width: 100%;">
    <tr>
      <td>সর্বমোট পণ্য:</td>
      <td class="text-right">{{ memo.lines|length }} টি</td>
    </tr>
    <tr class="grand-total">
      <td style="padding-top: 6px;">সর্বমোট (Grand Total):</td>
      <td class="text-right" style="padding-top: 6px;">৳{{ "%.2f"|format(memo.extracted_total or 0) }}</td>
    </tr>
  </table>
</div>

<div style="clear: both;"></div>

<div class="footer">
  সফটওয়্যার প্রস্তুতকারক: MemoLedger &bull; অটোমেটেড স্টক ও ইনভেন্টরি ম্যানেজমেন্ট &bull; ঢাকা, বাংলাদেশ
</div>

</body>
</html>
"""


class PDFInvoiceGenerator:
    @staticmethod
    def generate_pdf(memo: Memo) -> bytes:
        """
        Renders HTML invoice with Jinja2 and compiles to PDF via WeasyPrint.
        """
        import datetime
        tenant_name = memo.tenant.name if memo.tenant else "MemoLedger"
        supplier_name = memo.supplier.name if memo.supplier else "K Color Cosmetics"
        supplier_phone = memo.supplier.phone if memo.supplier else ""

        template = Template(HTML_INVOICE_TEMPLATE)
        html_content = template.render(
            memo=memo,
            tenant_name=tenant_name,
            supplier_name=supplier_name,
            supplier_phone=supplier_phone,
            current_date=datetime.datetime.now().strftime("%d-%m-%Y %I:%M %p")
        )

        try:
            from weasyprint import HTML
            pdf_bytes = HTML(string=html_content).write_pdf()
            return pdf_bytes
        except Exception:
            # Fallback for environments where native WeasyPrint cairo/pango isn't installed
            return html_content.encode("utf-8")
