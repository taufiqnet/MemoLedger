from typing import Dict, Any, Tuple

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None
    np = None


class ImagePreprocessor:
    @staticmethod
    def detect_blur(image, threshold: float = 70.0) -> Tuple[bool, float]:
        if cv2 is None or np is None:
            return False, 150.0
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        is_blurry = laplacian_var < threshold
        return is_blurry, round(laplacian_var, 2)

    @staticmethod
    def detect_glare(image, threshold: float = 0.08) -> Tuple[bool, float]:
        if cv2 is None or np is None:
            return False, 0.0
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        glare_pixels = np.sum(gray >= 250)
        total_pixels = gray.size
        glare_ratio = float(glare_pixels) / float(total_pixels)
        has_glare = glare_ratio > threshold
        return has_glare, round(glare_ratio * 100, 2)

    @staticmethod
    def normalize_contrast(image):
        if cv2 is None or np is None:
            return image
        if len(image.shape) == 3:
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            cl = clahe.apply(l)
            limg = cv2.merge((cl, a, b))
            return cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
        else:
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            return clahe.apply(image)

    @staticmethod
    def deskew_and_correct(image):
        if cv2 is None or np is None:
            return image
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        blur = cv2.GaussianBlur(gray, (9, 9), 0)
        thresh = cv2.adaptiveThreshold(
            blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
        )
        coords = np.column_stack(np.where(thresh > 0))
        if coords.size == 0:
            return image

        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        elif angle > 45:
            angle = 90 - angle
        else:
            angle = -angle

        if abs(angle) > 0.5 and abs(angle) < 25:
            (h, w) = image.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            return cv2.warpAffine(
                image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
            )
        return image

    @classmethod
    def process_image(cls, image_bytes: bytes) -> Tuple[bytes, Dict[str, Any]]:
        if cv2 is None or np is None:
            return image_bytes, {
                "blur_variance": 150.0,
                "is_blurry": False,
                "glare_percentage": 0.0,
                "has_glare": False,
                "retake_recommended": False,
                "warnings": []
            }

        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return image_bytes, {"error": "Invalid image format"}

        is_blurry, blur_var = cls.detect_blur(img)
        has_glare, glare_pct = cls.detect_glare(img)
        
        enhanced = cls.normalize_contrast(img)
        deskewed = cls.deskew_and_correct(enhanced)

        _, buffer = cv2.imencode(".jpg", deskewed, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
        processed_bytes = buffer.tobytes()

        quality_report = {
            "blur_variance": blur_var,
            "is_blurry": is_blurry,
            "glare_percentage": glare_pct,
            "has_glare": has_glare,
            "retake_recommended": bool(is_blurry or has_glare),
            "warnings": []
        }
        if is_blurry:
            quality_report["warnings"].append("Image appears blurry. Consider retaking for better OCR accuracy.")
        if has_glare:
            quality_report["warnings"].append(f"Image has glare/hotspots ({glare_pct}% overexposed).")

        return processed_bytes, quality_report
