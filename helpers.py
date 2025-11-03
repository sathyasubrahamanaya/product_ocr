# helpers.py
import os
import re
import logging
from typing import Any, Dict, Optional, List, Tuple
from PIL import Image, ImageDraw
from scheamas.v0.schemas import ProductInfo
from mistralai import Mistral

logger = logging.getLogger(__name__)

def _parse_markdown_text(text: str) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    lines = text.splitlines()
    for l in lines:
        line = l.strip()
        lower = line.lower()
        # product name heuristics
        if lower.startswith("product name") or lower.startswith("name of product"):
            parts = line.split(":", 1)
            if len(parts) == 2:
                result["product_name"] = parts[1].strip()
        # brand
        if lower.startswith("brand"):
            parts = line.split(":", 1)
            if len(parts) == 2:
                result["brand"] = parts[1].strip()
        # manufacturer / produced by
        if lower.startswith("manufactured by") or lower.startswith("produced by"):
            parts = line.split(":", 1)
            if len(parts) == 2:
                result["manufacturer"] = parts[1].strip()
        # origin country
        if lower.startswith("origin country") or lower.startswith("originated from"):
            parts = line.split(":", 1)
            if len(parts) == 2:
                result["origin_country"] = parts[1].strip()
        # price
        m = re.search(r"(?:price|mrp)\s*[:\-]?\s*([₹$]\s?\d+[.,]?\d*)", line, re.IGNORECASE)
        if m and "price" not in result:
            result["price"] = m.group(1).strip()
        # weight
        m = re.search(r"\bweight\s*[:\-]?\s*(\d+(?:\.\d+)?\s*(?:g|kg|ml|l))\b", line, re.IGNORECASE)
        if m and "weight" not in result:
            result["weight"] = m.group(1).strip()
        # size
        m = re.search(r"\bsize\s*[:\-]?\s*(\d+(?:\.\d+)?\s*(?:cm|mm|inch|in))\b", line, re.IGNORECASE)
        if m and "size" not in result:
            result["size"] = m.group(1).strip()
        # ingredients
        if lower.startswith("ingredients"):
            parts = line.split(":", 1)
            if len(parts) == 2 and "ingredients" not in result:
                result["ingredients"] = parts[1].strip()
        # dietary flags
        if "halal" in lower and ("yes" in lower or "certified" in lower):
            result["halal"] = True
        if "gluten free" in lower or "gluten-free" in lower:
            result["gluten_free"] = True
        # flavour
        m = re.search(r"\bflavour\s*[:\-]?\s*([A-Za-z ]+)", line, re.IGNORECASE)
        if m and "flavour" not in result:
            result["flavour"] = m.group(1).strip()
        # item count / no of packs
        m = re.search(r"\bitem[s]?\s*count\s*[:\-]?\s*(\d+)", line, re.IGNORECASE)
        if m and "item_count" not in result:
            result["item_count"] = m.group(1).strip()
        m = re.search(r"\bno(?:\.| of)?\s*pack(?:s)?\s*[:\-]?\s*(\d+)", line, re.IGNORECASE)
        if m and "no_of_packs" not in result:
            result["no_of_packs"] = m.group(1).strip()
    return result

def extract_product_info_from_ocr(ocr_response: Any) -> ProductInfo:
    extracted: Dict[str, Any] = {}
    # If structured annotation supported
    if hasattr(ocr_response, "document_annotation") and ocr_response.document_annotation:
        extracted.update(ocr_response.document_annotation)
    # If bbox_annotation supported
    if hasattr(ocr_response, "bbox_annotation") and ocr_response.bbox_annotation:
        if isinstance(ocr_response.bbox_annotation, dict):
            for k, v in ocr_response.bbox_annotation.items():
                if k not in extracted:
                    extracted[k] = v
        elif isinstance(ocr_response.bbox_annotation, list):
            for item in ocr_response.bbox_annotation:
                key = item.get("key")
                val = item.get("value")
                if key and val and key not in extracted:
                    extracted[key] = val
    # Fallback to markdown
    if hasattr(ocr_response, "pages"):
        full_text = "\n".join(
            page.markdown for page in ocr_response.pages if hasattr(page, "markdown")
        )
        heuristics = _parse_markdown_text(full_text)
        for k, v in heuristics.items():
            if k not in extracted:
                extracted[k] = v
    logger.info("Extracted data keys: %s", list(extracted.keys()))
    try:
        product_info = ProductInfo(**extracted)
    except Exception as e:
        logger.warning("Validation error building ProductInfo: %s — data: %s", e, extracted)
        valid = {k: v for k, v in extracted.items() if k in ProductInfo.__fields__}
        product_info = ProductInfo(**valid)
    return product_info

def draw_bounding_boxes_on_image(image: Image.Image, ocr_response: Any) -> Image.Image:
    img = image.copy()
    draw = ImageDraw.Draw(img)
    if hasattr(ocr_response, "pages"):
        for page in ocr_response.pages:
            if hasattr(page, "boxes") and isinstance(page.boxes, list):
                for box in page.boxes:
                    try:
                        x0, y0, x1, y1 = box
                        draw.rectangle([x0, y0, x1, y1], outline="red", width=2)
                    except Exception:
                        pass
    if hasattr(ocr_response, "bbox_annotation") and isinstance(ocr_response.bbox_annotation, list):
        for item in ocr_response.bbox_annotation:
            coords = item.get("bbox")
            if coords and len(coords) == 4:
                draw.rectangle(coords, outline="blue", width=2)
    return img

def process_image_file(image_path: str,
                       client: Mistral,
                       model_name: str,
                       annotation_schema: Optional[Dict] = None) -> Tuple[Optional[ProductInfo], Optional[Image.Image], Optional[str]]:
    try:
        with open(image_path, "rb") as f:
            content = f.read()
        upload = client.files.upload(
            file={
                "file_name": os.path.basename(image_path),
                "content": content
            },
            purpose="ocr"
        )
        file_id = upload.id
        signed = client.files.get_signed_url(file_id=file_id, expiry=24)
        url = signed.url
        logger.info("Uploaded and got signed URL: %s", url)
        response = client.ocr.process(
            model=model_name,
            document={
                "type": "document_url",
                "document_url": url
            },
            include_image_base64=False,
            # If you have annotation schema support, you could pass:
            # document_annotation_format=annotation_schema
        )
        info = extract_product_info_from_ocr(response)
        orig_img = Image.open(image_path)
        annotated_img = draw_bounding_boxes_on_image(orig_img, response)
        return info, annotated_img, None
    except Exception as e:
        logger.error("Error processing %s: %s", image_path, e)
        return None, None, str(e)

def process_batch_images(image_paths: List[str],
                         client: Mistral,
                         model_name: str,
                         annotation_schema: Optional[Dict] = None,
                         max_workers: int = 4) -> List[Dict[str, Any]]:
    import concurrent.futures
    results: List[Dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(process_image_file, path, client, model_name, annotation_schema): path
            for path in image_paths
        }
        for future in concurrent.futures.as_completed(futures):
            path = futures[future]
            try:
                info, annotated_img, error = future.result()
                results.append({"path": path, "info": info, "annotated_img": annotated_img, "error": error})
            except Exception as exc:
                logger.error("Unhandled exception for %s: %s", path, exc)
                results.append({"path": path, "info": None, "annotated_img": None, "error": str(exc)})
    return results
