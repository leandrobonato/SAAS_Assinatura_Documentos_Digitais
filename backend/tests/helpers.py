import base64
import io

from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def make_sample_pdf(pages: int = 2) -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    for i in range(pages):
        c.drawString(72, 720, f"Contrato de teste — página {i + 1}")
        c.showPage()
    c.save()
    return buffer.getvalue()


def make_signature_data_url() -> str:
    image = Image.new("RGBA", (120, 40), (0, 0, 0, 0))
    for x in range(10, 110):
        image.putpixel((x, 20), (20, 20, 160, 255))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()
