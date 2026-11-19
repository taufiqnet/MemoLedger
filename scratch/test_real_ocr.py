import re
from rapidocr_onnxruntime import RapidOCR
from PIL import Image
import numpy as np

ocr = RapidOCR()

def extract_from_image(image_path: str):
    result, _ = ocr(image_path)
    if not result:
        return {"supplier_header": {}, "lines": [], "written_total_raw": "0"}

    # Sort blocks by Y coordinate (top to bottom)
    # bbox is [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
    sorted_blocks = []
    for bbox, text, score in result:
        ymin = min(pt[1] for pt in bbox)
        xmin = min(pt[0] for pt in bbox)
        ymax = max(pt[1] for pt in bbox)
        xmax = max(pt[0] for pt in bbox)
        sorted_blocks.append({
            "text": text.strip(),
            "score": score,
            "bbox": [ymin, xmin, ymax, xmax]
        })
    sorted_blocks.sort(key=lambda b: b["bbox"][0])

    # Find memo number: look for 3 to 6 digits in top 35% of image
    memo_number = None
    for b in sorted_blocks:
        if b["bbox"][0] < 1200: # top portion
            m = re.search(r'\b(\d{3,6})\b', b["text"])
            if m:
                memo_number = m.group(1)
                break

    print(f"File: {image_path}")
    print(f"Detected Memo Number: {memo_number}")
    print(f"Total Text Blocks: {len(sorted_blocks)}")
    return memo_number, sorted_blocks

extract_from_image('data/uploads/memos/1c34438b-5dc5-43b6-b351-7590c6239315/5dbd32730e14cf47_memo_capture.jpg')
extract_from_image('app/static/samples/k_color_memo_sample.jpg')
