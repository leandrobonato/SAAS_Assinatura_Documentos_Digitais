"""PDF manipulation: signature overlay, hashing and the authenticity
certificate page. Uses pypdf for reading/merging pages and reportlab to draw
the overlay/certificate content, avoiding any dependency on a real
certificate authority or notary integration -- this generates a
verifiable-by-hash proof of authenticity, not a legally notarized document.
"""

import base64
import hashlib
import io
from datetime import datetime

from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


def get_page_count(pdf_bytes: bytes) -> int:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    return len(reader.pages)


def decode_signature_image(data_url: str) -> bytes:
    if "," in data_url:
        data_url = data_url.split(",", 1)[1]
    return base64.b64decode(data_url)


def apply_signature(pdf_bytes: bytes, fields: list[dict], signature_png: bytes, label: str) -> bytes:
    """Overlay the signature image (plus a small audit label) onto each
    field's position. Coordinates in `fields` are relative (0-1), with
    origin at the TOP-LEFT of the page (matching react-pdf's rendering),
    converted here to PDF's bottom-left origin."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    writer = PdfWriter()
    writer.append(reader)  # pages must belong to the writer before merge_page()

    fields_by_page: dict[int, list[dict]] = {}
    for f in fields:
        fields_by_page.setdefault(f["page_number"], []).append(f)

    image_reader = ImageReader(io.BytesIO(signature_png))

    for index, page in enumerate(writer.pages):
        page_fields = fields_by_page.get(index, [])
        if page_fields:
            width = float(page.mediabox.width)
            height = float(page.mediabox.height)
            buffer = io.BytesIO()
            c = canvas.Canvas(buffer, pagesize=(width, height))
            for f in page_fields:
                fw = f["width"] * width
                fh = f["height"] * height
                fx = f["x"] * width
                fy = height - (f["y"] * height) - fh
                c.drawImage(
                    image_reader, fx, fy, width=fw, height=fh,
                    mask="auto", preserveAspectRatio=True, anchor="sw",
                )
                c.setFont("Helvetica", max(6, min(8, fh * 0.3)))
                c.setFillColorRGB(0.25, 0.25, 0.25)
                c.drawString(fx, max(fy - 9, 2), label)
            c.save()
            buffer.seek(0)
            overlay_reader = PdfReader(buffer)
            page.merge_page(overlay_reader.pages[0])

    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def generate_certificate_page(document_title: str, original_hash: str, signers: list[dict]) -> bytes:
    buffer = io.BytesIO()
    width, height = A4
    c = canvas.Canvas(buffer, pagesize=A4)

    y = height - 60
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, "Certificado de Autenticidade — DocuFlow")
    y -= 28
    c.setFont("Helvetica", 10)
    c.drawString(50, y, f"Documento: {document_title}")
    y -= 16
    c.drawString(50, y, f"Hash SHA-256 do documento original: {original_hash}")
    y -= 26

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Trilha de assinaturas")
    y -= 20
    c.setFont("Helvetica", 9)

    for s in signers:
        lines = [
            f"Signatário: {s['name']} <{s['email']}>",
            f"Assinado em (UTC): {s['signed_at']}",
            f"Endereço IP: {s.get('ip_address') or 'N/D'}",
            f"Navegador/Agente: {(s.get('user_agent') or 'N/D')[:100]}",
        ]
        for line in lines:
            c.drawString(60, y, line)
            y -= 13
        y -= 8
        if y < 80:
            c.showPage()
            c.setFont("Helvetica", 9)
            y = height - 60

    y -= 10
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(50, y, f"Gerado automaticamente pelo DocuFlow em {datetime.utcnow().isoformat()}Z")
    c.save()
    buffer.seek(0)
    return buffer.getvalue()


def append_pages(pdf_bytes: bytes, extra_pdf_bytes: bytes) -> bytes:
    reader_main = PdfReader(io.BytesIO(pdf_bytes))
    reader_extra = PdfReader(io.BytesIO(extra_pdf_bytes))
    writer = PdfWriter()
    for page in reader_main.pages:
        writer.add_page(page)
    for page in reader_extra.pages:
        writer.add_page(page)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()
