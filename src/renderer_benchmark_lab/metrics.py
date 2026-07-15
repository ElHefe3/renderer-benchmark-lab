from __future__ import annotations

import re
import statistics
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

import fitz
import numpy as np
from PIL import Image
from skimage.metrics import structural_similarity


def rasterize(pdf: Path, dpi: int, destination: Path) -> dict:
    document = fitz.open(pdf)
    pages, texts, sizes, blanks = [], [], [], []
    resources = {"images": 0, "drawings": 0}
    destination.mkdir(parents=True, exist_ok=True)
    for index, page in enumerate(document):
        pix = page.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72), alpha=False)
        array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)[..., :3].copy()
        pages.append(array)
        texts.append(" ".join(page.get_text("text").split()))
        sizes.append([page.rect.width, page.rect.height])
        resources["images"] += len(page.get_images(full=True))
        resources["drawings"] += len(page.get_drawings())
        if float(np.mean(np.min(array, axis=2) < 245)) < .0001:
            blanks.append(index + 1)
        Image.fromarray(array).save(destination / f"page-{index + 1}.png")
    document.close()
    return {"pages": pages, "texts": texts, "sizes": sizes, "blank_pages": blanks, "resources": resources}


def _pad(left, right):
    height = max(left.shape[0] if left is not None else 1, right.shape[0] if right is not None else 1)
    width = max(left.shape[1] if left is not None else 1, right.shape[1] if right is not None else 1)
    def one(value):
        canvas = np.full((height, width, 3), 255, dtype=np.uint8)
        if value is not None:
            canvas[:value.shape[0], :value.shape[1]] = value
        return canvas
    return one(left), one(right)


def _bbox(page):
    ys, xs = np.where(np.min(page, axis=2) < 245)
    return None if not len(xs) else (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)


def _iou(left, right):
    if left is None or right is None:
        return 1.0 if left is right else 0.0
    x1, y1, x2, y2 = max(left[0], right[0]), max(left[1], right[1]), min(left[2], right[2]), min(left[3], right[3])
    intersection = max(0, x2 - x1) * max(0, y2 - y1)
    union = (left[2]-left[0])*(left[3]-left[1]) + (right[2]-right[0])*(right[3]-right[1]) - intersection
    return intersection / union if union else 1.0


def compare(reference: dict, candidate: dict, diff_dir: Path, required_text: tuple[str, ...] = ()) -> dict:
    ssims, pixels, boxes, ink = [], [], [], []
    for index in range(max(len(reference["pages"]), len(candidate["pages"]))):
        left, right = _pad(reference["pages"][index] if index < len(reference["pages"]) else None,
                           candidate["pages"][index] if index < len(candidate["pages"]) else None)
        ssims.append(float(structural_similarity(left, right, channel_axis=2, data_range=255)))
        pixels.append(float(np.mean(np.abs(left.astype(np.int16) - right.astype(np.int16))) / 255))
        boxes.append(_iou(_bbox(left), _bbox(right)))
        ink.append(float(np.mean(np.min(right, axis=2) < 245) - np.mean(np.min(left, axis=2) < 245)))
        Image.fromarray(np.max(np.abs(left.astype(np.int16)-right.astype(np.int16)), axis=2).astype(np.uint8)).save(diff_dir / f"page-{index+1}.png")
    left_text, right_text = " ".join(reference["texts"]), " ".join(candidate["texts"])
    left_words, right_words = Counter(left_text.lower().split()), Counter(right_text.lower().split())
    common = sum((left_words & right_words).values())
    required_missing = [value for value in required_text if value.lower() not in right_text.lower()]
    categories = {
        "text": statistics.fmean([(1-common/max(1,sum(left_words.values())))*100,
                                   (1-common/max(1,sum(right_words.values())))*100,
                                   (1-SequenceMatcher(None,left_text,right_text).ratio())*100]),
        "layout": statistics.fmean([(1-statistics.fmean(boxes))*100, min(100, abs(statistics.fmean(ink))*500)]),
        "pagination": statistics.fmean([min(100, abs(len(candidate["pages"])-len(reference["pages"]))/max(1,len(reference["pages"]))*100),
                                         min(100, abs(len(candidate["blank_pages"])-len(reference["blank_pages"]))/max(1,len(reference["pages"]))*100)]),
        "assets": statistics.fmean([_relative(reference["resources"]["images"],candidate["resources"]["images"])*100,
                                     _relative(reference["resources"]["drawings"],candidate["resources"]["drawings"])*100]),
        "visual": statistics.fmean([(1-statistics.fmean(ssims))*100, statistics.fmean(pixels)*100]),
    }
    return {"categories": categories, "required_text_missing": required_missing,
            "ssim": statistics.fmean(ssims), "pixel_error": statistics.fmean(pixels)}


def _relative(left, right):
    return min(1.0, abs(left-right)/max(1,left))


def complexity(html: Path) -> dict:
    source = html.read_text(encoding="utf-8")
    return {"html_bytes": len(source.encode()), "element_count": len(re.findall(r"<[A-Za-z][^>]*>", source)),
            "css_rule_count": source.count("{")}

