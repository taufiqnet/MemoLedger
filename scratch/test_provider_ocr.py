import io
import re
import numpy as np
from PIL import Image
from rapidocr_onnxruntime import RapidOCR

engine = RapidOCR()

def test_ocr_provider(img_path):
    with open(img_path, 'rb') as f:
        image_bytes = f.read()

    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    w_img, h_img = img.size
    arr = np.array(img)

    results, _ = engine(arr)
    if not results:
        print(f"[{img_path}] No OCR text detected!")
        return

    # Sort blocks by Y
    blocks = []
    for bbox, text, score in results:
        ymin = min(pt[1] for pt in bbox)
        xmin = min(pt[0] for pt in bbox)
        ymax = max(pt[1] for pt in bbox)
        xmax = max(pt[0] for pt in bbox)
        blocks.append({
            "text": text.strip(),
            "score": score,
            "bbox_norm": [
                int(ymin / h_img * 1000),
                int(xmin / w_img * 1000),
                int(ymax / h_img * 1000),
                int(xmax / w_img * 1000)
            ],
            "ymin": ymin
        })
    blocks.sort(key=lambda b: b["ymin"])

    # Extract memo number from top 30%
    memo_num = None
    for b in blocks:
        if b["bbox_norm"][0] < 300:
            m = re.search(r'\b(\d{3,6})\b', b["text"])
            if m:
                memo_num = m.group(1)
                break

    print(f"\n==========================================")
    print(f"IMAGE: {img_path}")
    print(f"DIMENSIONS: {w_img}x{h_img}")
    print(f"DETECTED MEMO NUMBER FROM OCR: {memo_num}")
    print(f"TOTAL DETECTED BLOCKS: {len(blocks)}")
    print(f"FIRST 5 BLOCKS:")
    for b in blocks[:5]:
        print(f"  - [{b['score']:.2f}] '{b['text']}' @ {b['bbox_norm']}")

test_ocr_provider('data/uploads/memos/1c34438b-5dc5-43b6-b351-7590c6239315/5dbd32730e14cf47_memo_capture.jpg')
test_ocr_provider('app/static/samples/k_color_memo_sample.jpg')
