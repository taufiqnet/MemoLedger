import io
import csv
from typing import List
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from app.models.memo import Memo


class SpreadsheetExporter:
    @staticmethod
    def export_memo_csv(memo: Memo) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Line No", "Raw Text", "Parsed Item", "Variant", "Quantity", "Unit", "Unit Price (BDT)", "Line Total (BDT)", "Status"])
        for line in memo.lines:
            writer.writerow([
                line.line_number,
                line.raw_text,
                line.parsed_name or "",
                line.parsed_variant or "",
                line.parsed_qty,
                line.parsed_unit,
                line.parsed_unit_price or 0,
                line.parsed_line_total or 0,
                line.status
            ])
        writer.writerow([])
        writer.writerow(["Total BDT", "", "", "", "", "", "", memo.extracted_total or 0, ""])
        return output.getvalue()

    @staticmethod
    def export_memo_excel(memo: Memo) -> bytes:
        wb = Workbook()
        ws = wb.active
        ws.title = f"Memo_{memo.memo_number or 'Details'}"

        headers = ["Line", "Item Name", "Variant", "Qty", "Unit", "Rate (BDT)", "Total (BDT)", "Status"]
        ws.append(headers)

        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="0F766E", end_color="0F766E", fill_type="solid")
        
        for col_idx, _ in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")

        for line in memo.lines:
            ws.append([
                line.line_number,
                line.parsed_name or line.raw_text,
                line.parsed_variant or "-",
                float(line.parsed_qty),
                line.parsed_unit,
                float(line.parsed_unit_price or 0),
                float(line.parsed_line_total or 0),
                line.status
            ])

        ws.append([])
        ws.append(["", "", "", "", "Grand Total:", "", float(memo.extracted_total or 0), ""])

        # Auto-adjust column widths
        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = col[0].column_letter
            ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

        out = io.BytesIO()
        wb.save(out)
        return out.getvalue()
