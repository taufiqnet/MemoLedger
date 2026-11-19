import urllib.parse
from app.models.memo import Memo


class WhatsAppShareLink:
    @staticmethod
    def generate_link(memo: Memo, base_url: str = "http://localhost:8000") -> str:
        """
        Generates a click-to-chat WhatsApp link with formatted item breakdown.
        """
        phone = memo.supplier.phone if (memo.supplier and memo.supplier.phone) else ""
        clean_phone = "".join(c for c in phone if c.isdigit())
        if clean_phone.startswith("0"):
            clean_phone = "88" + clean_phone

        supplier_name = memo.supplier.name if memo.supplier else "Supplier"
        text_lines = [
            f"*মেমো ভাউচার (Memo #{memo.memo_number or 'N/A'})*",
            f"সরবরাহকারী: {supplier_name}",
            f"তারিখ: {memo.memo_date or 'N/A'}",
            "------------------------",
        ]

        for line in memo.lines:
            item_name = line.parsed_name or line.raw_text
            variant = f" ({line.parsed_variant})" if line.parsed_variant else ""
            qty = f"{line.parsed_qty} {line.parsed_unit}"
            total = f"৳{line.parsed_line_total or 0}"
            text_lines.append(f"• {item_name}{variant}: {qty} = {total}")

        text_lines.append("------------------------")
        text_lines.append(f"*সর্বমোট: ৳{memo.extracted_total or 0}*")
        text_lines.append(f"অনলাইন ইনভয়েস লিংক: {base_url}/api/v1/memos/{memo.id}/pdf")

        message = "\n".join(text_lines)
        encoded_message = urllib.parse.quote(message)

        if clean_phone:
            return f"https://api.whatsapp.com/send?phone={clean_phone}&text={encoded_message}"
        else:
            return f"https://api.whatsapp.com/send?text={encoded_message}"
