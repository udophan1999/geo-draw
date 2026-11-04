"""Normalize phone/document uploads into ordered raster pages for the vision model."""

from __future__ import annotations

from io import BytesIO

RASTER_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}
HEIC_TYPES = {"image/heic", "image/heif"}
PDF_TYPE = "application/pdf"
UPLOAD_TYPES = RASTER_TYPES | HEIC_TYPES | {PDF_TYPE}
MAX_PAGES = 4
MAX_PIXELS = 30_000_000


def normalize_problem_file(data: bytes, mime_type: str) -> list[tuple[bytes, str]]:
    """Return one or more PNG/raster pages accepted by the vision endpoint."""
    mime_type = (mime_type or "").casefold()
    if not data:
        raise ValueError("Tệp đề bài đang trống.")
    if mime_type in RASTER_TYPES:
        return [(data, mime_type)]
    if mime_type in HEIC_TYPES:
        return [(_heic_to_png(data), "image/png")]
    if mime_type == PDF_TYPE:
        return [(page, "image/png") for page in _pdf_to_png_pages(data)]
    raise ValueError("Tệp phải là PNG, JPG, WEBP, GIF, HEIC, HEIF hoặc PDF.")


def _heic_to_png(data: bytes) -> bytes:
    try:
        from PIL import Image
        from pillow_heif import register_heif_opener
    except ImportError as exc:  # pragma: no cover - deployment dependency guard
        raise ValueError("Máy chủ chưa cài bộ đọc HEIC; hãy đổi ảnh sang JPG hoặc PNG.") from exc
    register_heif_opener()
    try:
        with Image.open(BytesIO(data)) as image:
            if image.width * image.height > MAX_PIXELS:
                raise ValueError("Ảnh HEIC có độ phân giải quá lớn; hãy giảm kích thước rồi thử lại.")
            output = BytesIO()
            image.convert("RGB").save(output, format="PNG", optimize=True)
            return output.getvalue()
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("Không đọc được ảnh HEIC; tệp có thể bị hỏng.") from exc


def _pdf_to_png_pages(data: bytes) -> list[bytes]:
    try:
        import pymupdf
    except ImportError as exc:  # pragma: no cover - deployment dependency guard
        raise ValueError("Máy chủ chưa cài bộ đọc PDF; hãy xuất từng trang thành ảnh.") from exc
    try:
        document = pymupdf.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise ValueError("Không đọc được tệp PDF; tệp có thể bị hỏng hoặc có mật khẩu.") from exc
    try:
        if document.needs_pass:
            raise ValueError("PDF có mật khẩu; hãy mở khóa tệp rồi gửi lại.")
        if document.page_count < 1:
            raise ValueError("PDF không có trang nào.")
        if document.page_count > MAX_PAGES:
            raise ValueError("Mỗi lượt nhận tối đa 4 trang PDF; hãy tách tệp thành các phần nhỏ hơn.")
        pages = []
        for page in document:
            longest = max(float(page.rect.width), float(page.rect.height), 1.0)
            scale = min(2.5, 2400.0 / longest)
            pixmap = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False)
            pages.append(pixmap.tobytes("png"))
        return pages
    finally:
        document.close()
