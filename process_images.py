import os
import json
import re
from typing import List, Tuple, Dict, Any

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

try:
    import easyocr  # type: ignore
except Exception as e:
    raise RuntimeError(f"EasyOCR is required but failed to import: {e}")


FA_CHAR_PATTERN = re.compile(r"[\u0600-\u06FF]")


def contains_persian(text: str) -> bool:
    return bool(FA_CHAR_PATTERN.search(text))


def normalize_digits_to_western(text: str) -> str:
    fa_digits = "۰۱۲۳۴۵۶۷۸۹"
    ar_digits = "٠١٢٣٤٥٦٧٨٩"
    mapping: Dict[str, str] = {}
    for i, d in enumerate(fa_digits):
        mapping[d] = str(i)
    for i, d in enumerate(ar_digits):
        mapping[d] = str(i)
    return "".join(mapping.get(ch, ch) for ch in text)


IRANIAN_MONTHS_MAP = {
    # Persian month names -> English transliterations
    "فروردین": "Farvardin",
    "اردیبهشت": "Ordibehesht",
    "خرداد": "Khordad",
    "تیر": "Tir",
    "مرداد": "Mordad",
    "شهریور": "Shahrivar",
    "مهر": "Mehr",
    "آبان": "Aban",
    "آذر": "Azar",
    "دی": "Dey",
    "بهمن": "Bahman",
    "اسفند": "Esfand",
}


def apply_custom_terms(english_text: str, original_fa: str) -> str:
    # Enforce required naming for school
    fa = original_fa or ""
    school_regexes = [
        r"علام[هۀ]\s+حل[یىي]\s*(?:6|٦|شش)?",  # علامه حلی 6 variants
        r"علام[هۀ]\s+عل[یىي]\s*(?:6|٦|شش)",   # OCR: حلی -> علی
        r"دبیرستان\s+علام[هۀ]\s+حل[یىي]\s*(?:6|٦|شش)?",
        r"حلى\s*(?:6|٦|شش)?",                  # Arabic yeh variant
    ]
    for pat in school_regexes:
        if re.search(pat, fa):
            return "Allame Heli 6"

    # Common domain terms normalization when the original clearly matches
    term_map = [
        (r"جمهور[یى]\s+اسلام[یى]\s+ا?یران", "Islamic Republic of Iran"),
        (r"وزارت\s+آموزش(?:\s+و)?\s+پرورش", "Ministry of Education"),
        (r"استان\s+تهران", "Tehran Province"),
        (r"نام\s+و\s*نام\s+خانواد(?:گ(?:ی|ى)|كى)", "Full name"),
        (r"نام\s+درس", "Course name"),
        (r"کلاس|كلاس", "Class"),
        (r"پایه(?:\s+تحصیلی)?", "Grade"),
        (r"سال\s+تحصیلی", "Academic Year"),
        (r"نمره\s+نهایی", "Final score"),
        (r"نهایی", "Final"),
        (r"رتبه\s+در", "Rank in"),
        (r"منطقه", "District"),
        (r"مجموع\s*:?", "Total:"),
        (r"معدل\s+کل", "Overall GPA"),
        (r"تفكر\s+وسبك\s+زندگ[یى]", "Thinking and Lifestyle"),
        (r"برنامه\s+نويس[یى]", "Programming"),
        (r"هندسه", "Geometry"),
        (r"پیام(?:\s+های)?\s+آسمان(?:[یى])?", "Heavenly Messages"),
        (r"فیز(?:یک|يك|بک)", "Physics"),
        (r"زيست\s+شناسی|زیست\s+شناسی", "Biology"),
        (r"زبان\s+انگلیسی|زبان\s+انکلیسی|زبان\s+انكليسى", "English Language"),
        (r"املا", "Spelling"),
        (r"ادبیات|ادبمات", "Literature"),
        (r"ریاض[یى]|ریافی|رىاضی", "Mathematics"),
        (r"فرهنگ\s+و\s+هنر|فرهنك\s+وهنر", "Arts & Culture"),
        (r"مطالعات\s+اجتماع[یى]", "Social Studies"),
        (r"زمین\s+شناسی|زمين\s+شناسی", "Geology"),
        (r"پژوهش|پروهش", "Research"),
    ]
    for pat, replacement in term_map:
        if re.search(pat, fa):
            return replacement

    # Minor normalization of school name in any English guess
    english_text = (english_text or "").replace("Allame Helli 6", "Allame Heli 6").replace("Allame Helli", "Allame Heli")
    return english_text


def postprocess_english(text_en: Any) -> str:
    # Collapse excessive whitespace and fix common tokenization artifacts
    if not isinstance(text_en, str):
        return ""
    text = re.sub(r"\s+", " ", text_en).strip()
    # Replace Persian percent sign etc.
    text = text.replace("٪", "%")
    return text


def translate_fa_to_en(text_fa: str) -> str:
    # Normalize digits first
    text_norm = normalize_digits_to_western(text_fa)

    # Translate months explicitly to avoid wrong calendar conversion
    for fa_name, en_name in IRANIAN_MONTHS_MAP.items():
        text_norm = text_norm.replace(fa_name, en_name)

    # Use deep-translator with automatic detection
    try:
        from deep_translator import GoogleTranslator  # type: ignore
        translated_obj = GoogleTranslator(source='auto', target='en').translate(text_norm)
    except Exception:
        translated_obj = None

    translated_pp = postprocess_english(translated_obj)
    translated = translated_pp if translated_pp else text_norm
    translated = apply_custom_terms(translated, text_fa)
    return translated


def polygon_to_bbox(poly: List[List[float]]) -> Tuple[int, int, int, int]:
    xs = [int(p[0]) for p in poly]
    ys = [int(p[1]) for p in poly]
    return min(xs), min(ys), max(xs), max(ys)


def expand_bbox(bbox: Tuple[int, int, int, int], image_shape: Tuple[int, int, int], pad: int = 4) -> Tuple[int, int, int, int]:
    h, w = image_shape[:2]
    x1, y1, x2, y2 = bbox
    x1 = max(0, x1 - pad)
    y1 = max(0, y1 - pad)
    x2 = min(w - 1, x2 + pad)
    y2 = min(h - 1, y2 + pad)
    return x1, y1, x2, y2


def dominant_text_color(bgr_region: np.ndarray) -> Tuple[int, int, int]:
    # Heuristic: cluster colors (k=2) and select the one with higher contrast to median background
    region = bgr_region.reshape(-1, 3).astype(np.float32)
    if region.size == 0:
        return (0, 0, 0)
    k = 2
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 0.5)
    try:
        _, labels, centers = cv2.kmeans(region, k, None, criteria, 3, cv2.KMEANS_PP_CENTERS)
        centers = centers.astype(np.uint8)
        counts = np.bincount(labels.flatten(), minlength=k)
        # Assume the less frequent color is text color (often true for text on background)
        text_center = centers[np.argmin(counts)]
        return tuple(int(c) for c in text_center.tolist())
    except Exception:
        mean_color = tuple(int(c) for c in region.mean(axis=0).tolist())
        return mean_color


def choose_contrasting_color(bgr: Tuple[int, int, int]) -> Tuple[int, int, int]:
    # YIQ luma approximation for brightness
    b, g, r = bgr
    brightness = (0.299 * r + 0.587 * g + 0.114 * b)
    return (0, 0, 0) if brightness > 160 else (255, 255, 255)


def draw_text_within_bbox(pil_img: Image.Image, text: str, bbox: Tuple[int, int, int, int], text_bgr: Tuple[int, int, int]) -> None:
    draw = ImageDraw.Draw(pil_img)
    x1, y1, x2, y2 = bbox
    width = max(1, x2 - x1)
    height = max(1, y2 - y1)

    # Try to use a common sans font; fallback to default if unavailable
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    font = None
    for p in font_paths:
        if os.path.exists(p):
            try:
                font = ImageFont.truetype(p, size=height)
                break
            except Exception:
                continue
    if font is None:
        font = ImageFont.load_default()

    # Convert BGR to RGB
    text_rgb = (int(text_bgr[2]), int(text_bgr[1]), int(text_bgr[0]))
    stroke_rgb = (0, 0, 0) if sum(text_rgb) > 382 else (255, 255, 255)

    # Find max font size that fits; allow multi-line wrapping
    def fits(font_obj: ImageFont.FreeTypeFont, wrapped: List[str]) -> bool:
        total_h = 0
        max_w = 0
        for line in wrapped:
            bbox_line = draw.textbbox((0, 0), line, font=font_obj, stroke_width=max(1, font_obj.size // 18))
            w = bbox_line[2] - bbox_line[0]
            h = bbox_line[3] - bbox_line[1]
            total_h += h
            max_w = max(max_w, w)
        # Add small line spacing
        total_h += max(1, len(wrapped) - 1) * max(1, font_obj.size // 6)
        return max_w <= width and total_h <= height

    def wrap_text(text_in: str, font_obj: ImageFont.FreeTypeFont) -> List[str]:
        words = text_in.split()
        lines: List[str] = []
        current = ""
        for w in words:
            test = (current + " " + w).strip()
            bbox_test = draw.textbbox((0, 0), test, font=font_obj, stroke_width=max(1, font_obj.size // 18))
            tw = bbox_test[2] - bbox_test[0]
            if tw <= width or not current:
                current = test
            else:
                lines.append(current)
                current = w
        if current:
            lines.append(current)
        return lines

    # Binary search font size
    low, high = 6, max(10, height)
    best_lines: List[str] = [text]
    best_font = font
    while low <= high:
        mid = (low + high) // 2
        try:
            trial_font = ImageFont.truetype(font.path if hasattr(font, 'path') else font_paths[0], size=mid)
        except Exception:
            trial_font = font
        lines = wrap_text(text, trial_font)
        if fits(trial_font, lines):
            best_font = trial_font
            best_lines = lines
            low = mid + 1
        else:
            high = mid - 1

    # Vertical centering
    total_h = 0
    line_heights: List[int] = []
    for line in best_lines:
        b = draw.textbbox((0, 0), line, font=best_font, stroke_width=max(1, best_font.size // 18))
        line_heights.append(b[3] - b[1])
        total_h += (b[3] - b[1])
    total_h += max(1, len(best_lines) - 1) * max(1, best_font.size // 6)
    y = y1 + max(0, (height - total_h) // 2)

    # Draw each line, left aligned (LTR)
    for idx, line in enumerate(best_lines):
        b = draw.textbbox((0, 0), line, font=best_font, stroke_width=max(1, best_font.size // 18))
        line_h = b[3] - b[1]
        draw.text(
            (x1, y),
            line,
            font=best_font,
            fill=text_rgb,
            stroke_width=max(1, best_font.size // 18),
            stroke_fill=stroke_rgb,
        )
        y += line_h + max(1, best_font.size // 6)


def inpaint_regions(bgr_img: np.ndarray, polys: List[List[List[float]]]) -> np.ndarray:
    mask = np.zeros(bgr_img.shape[:2], dtype=np.uint8)
    for poly in polys:
        pts = np.array(poly, dtype=np.int32)
        cv2.fillPoly(mask, [pts], 255)
    # Dilate mask slightly to ensure full coverage
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.dilate(mask, kernel, iterations=1)
    inpainted = cv2.inpaint(bgr_img, mask, 3, cv2.INPAINT_TELEA)
    return inpainted


def process_image(input_path: str, output_image_path: str, output_json_path: str) -> None:
    bgr = cv2.imread(input_path, cv2.IMREAD_COLOR)
    if bgr is None:
        raise RuntimeError(f"Failed to read image: {input_path}")

    reader = easyocr.Reader(['fa', 'ar', 'en'], gpu=False)
    results = reader.readtext(bgr)

    segments: List[Dict[str, Any]] = []
    polys_to_remove: List[List[List[float]]] = []

    # First pass: collect Persian segments
    for res in results:
        # res: [box, text, confidence]
        poly, text, conf = res
        if not isinstance(text, str):
            continue
        if contains_persian(text):
            x1, y1, x2, y2 = polygon_to_bbox(poly)
            x1, y1, x2, y2 = expand_bbox((x1, y1, x2, y2), bgr.shape, pad=4)
            polys_to_remove.append(poly)

            text_norm_digits = normalize_digits_to_western(text)
            text_en = translate_fa_to_en(text_norm_digits)
            segments.append({
                "bbox": [int(x1), int(y1), int(x2), int(y2)],
                "lang": "fa",
                "original": text,
                "english": text_en,
                "confidence": float(conf),
            })

    # Inpaint collected regions
    bgr_inpainted = inpaint_regions(bgr, polys_to_remove) if polys_to_remove else bgr.copy()

    # Overlay translated text
    pil_img = Image.fromarray(cv2.cvtColor(bgr_inpainted, cv2.COLOR_BGR2RGB))
    for seg in segments:
        x1, y1, x2, y2 = seg["bbox"]
        # Sample original region color from the original (pre-inpaint) image
        region = bgr[y1:y2, x1:x2]
        text_color_bgr = dominant_text_color(region)
        # Ensure good contrast if sampling failed
        if region.size == 0:
            text_color_bgr = (0, 0, 0)
        # If sampled color equals background-ish, pick contrasting color
        if np.linalg.norm(np.array(text_color_bgr) - np.array(region.mean(axis=(0, 1)) if region.size else np.array([255, 255, 255]))) < 25:
            text_color_bgr = choose_contrasting_color(tuple(int(c) for c in region.mean(axis=(0, 1))[:3])) if region.size else (0, 0, 0)

        draw_text_within_bbox(pil_img, seg["english"], (x1, y1, x2, y2), text_color_bgr)

    # Save PNG preserving original resolution
    pil_img.save(output_image_path, format="PNG")

    # Save transcript JSON
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(segments, f, ensure_ascii=False, indent=2)


def main() -> None:
    input_dir = "/workspace/input"
    output_dir = "/workspace/output"
    os.makedirs(output_dir, exist_ok=True)

    # Gather up to 5 images
    candidates = []
    for name in sorted(os.listdir(input_dir)):
        if name.lower().endswith((".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff")):
            candidates.append(name)
    # If there are specific 1..5.jpg files, keep their order
    priority = ["1.jpg", "2.jpg", "3.jpg", "4.jpg", "5.jpg"]
    ordered = [n for n in priority if n in candidates]
    remainder = [n for n in candidates if n not in ordered]
    images = (ordered + remainder)[:5]

    for fname in images:
        in_path = os.path.join(input_dir, fname)
        base, _ = os.path.splitext(fname)
        out_img = os.path.join(output_dir, f"{base}.png")
        out_json = os.path.join(output_dir, f"{base}.json")
        process_image(in_path, out_img, out_json)


if __name__ == "__main__":
    main()

