"""Local Sugarwood key-card agreement prototype.

Serves the static form and turns validated submissions into downloadable PDFs.
No submission data is transmitted anywhere and no email is sent.
"""

from __future__ import annotations

import io
import hashlib
import json
import re
import secrets
import zipfile
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from reportlab.lib.colors import HexColor, black
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"
GENERATED_DIR = ROOT / "generated"

AGREEMENT_PROFILES = {
    "nonresident": {
        "form_title": "Sugarwood Non-Resident/Associate Member Form",
        "email_label": "Non-Resident Key Card Access Agreement",
        "agreement_version": "KCAnonres-2026-11-19",
        "submission_prefix": "KC",
        "address_label": "Print Sugarwood Non-Resident/Associate Member Address:",
        "intro": (
            "By signing this Key Card Access Agreement, the below listed Key Card "
            "assignee agrees to the following:"
        ),
        "items": [
            "Key Card Access Privileges to SHA recreational facilities are granted annually.",
            "Key Card Privileges are offered to Sugarwood Non-Resident/Associate Members that have an approved Application for an Associate SHA Membership - Limited Recreation Areas Pass.",
            "SHA Board of Directors has sole authority to grant or revoke Sugarwood Non-Resident/Associate Membership and Key Card Access Privileges.",
            "Replacement Key Card for lost, stolen, damaged or destroyed will be $50 per Key Card.",
            "Misuse of Key Cards will result in Key Card Privileges being revoked.",
            "Key Cards are issued to and may be used ONLY by the Sugarwood Non-Resident/Associate Member's immediate family.",
            "Any individuals other than authorized Sugarwood Non-Resident/Associate Member's family utilizing the Key Card will constitute a Misuse of the key card and will result in the Key Card being Revoked.",
            "A $50 Refundable Deposit is required for the Sugarwood Non-Resident/Associate Member Key Card. If the Key Card is returned in good functioning order, to the SHA Board of Directors, the Key Card Deposit will be Mailed to the Sugarwood Non-Resident/Associate Member's Address.",
        ],
    },
    "resident": {
        "form_title": "Sugarwood Resident Key Card Agreement",
        "email_label": "Resident Key Card Access Agreement",
        "agreement_version": "KCAresident-2019-online-2026-11-19",
        "submission_prefix": "RKC",
        "address_label": "Print Property Address:",
        "intro": (
            "By signing this Key Card Access Agreement. The below listed property "
            "agrees to the following:"
        ),
        "items": [
            "Key Card Privileges are granted annually.",
            "Key Card Privileges are offered to property owners in good standing with their annual dues.",
            "SHA Board of Directors has sole authority to grant or revoke Key Card Privileges.",
            "Replacement Key Card for lost, stolen, damaged or destroyed will be $50 per Key Card.",
            "Misuse of Key Cards will result in Key Card Privileges being revoked.",
            "Key Cards are to be used by the Property Owners issued the Key Cards ONLY.",
            "Any individuals other than authorized Property Owners utilizing a Property Owners Key Card will constitute a Misuse of the key card and will result in key card being revoked.",
            "If SHA homeowner property is sold Key Card must be returned to SHA Board of Directors prior to closing of property for reissuance of Key Card to new property owner by SHA Board of Directors. If Key Card not returned to SHA Board of Directors a $50 key card replacement fee will be charged.",
        ],
    },
}


def agreement_profile(agreement_type: str = "nonresident") -> dict[str, object]:
    try:
        return AGREEMENT_PROFILES[agreement_type]
    except KeyError as exc:
        raise ValueError("Unknown agreement type.") from exc


# Backward-compatible aliases used by the existing non-resident configuration route.
FORM_TITLE = str(AGREEMENT_PROFILES["nonresident"]["form_title"])
AGREEMENT_VERSION = str(AGREEMENT_PROFILES["nonresident"]["agreement_version"])
INTRO = str(AGREEMENT_PROFILES["nonresident"]["intro"])
AGREEMENT_ITEMS = list(AGREEMENT_PROFILES["nonresident"]["items"])
RETURN_TEXT = (
    "Please return the Key Card Agreement to the SHA Board of Directors and allow "
    "2-3 weeks for processing and issuance of Key Card."
)
SIGNATURE_CONSENT = (
    "By typing my name below and selecting Submit signed agreement, I intend "
    "to electronically sign this Key Card Access Agreement. I consent to using an "
    "electronic record and confirm that the information I provided is accurate."
)

REQUIRED_TEXT_FIELDS = {
    "street": "Street",
    "city": "City",
    "state": "State",
    "zip": "ZIP code",
    "fullName": "Full name",
    "signature": "Signature",
    "phone": "Phone number",
    "email": "Email",
}


def clean_text(value: object, max_length: int = 160) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.strip().split())[:max_length]


def validate_submission(raw: object) -> tuple[dict[str, str | bool], list[str]]:
    if not isinstance(raw, dict):
        return {}, ["The request body must be a JSON object."]

    data: dict[str, str | bool] = {
        key: clean_text(raw.get(key)) for key in REQUIRED_TEXT_FIELDS
    }
    data["email2"] = clean_text(raw.get("email2"))
    data["acknowledged"] = raw.get("acknowledged") is True
    errors = [f"{label} is required." for key, label in REQUIRED_TEXT_FIELDS.items() if not data[key]]

    if data["email"] and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", str(data["email"])):
        errors.append("Email must be a valid address.")
    if data["email2"] and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", str(data["email2"])):
        errors.append("Optional second email must be a valid address.")
    if data["state"] and not re.fullmatch(r"[A-Za-z]{2}", str(data["state"])):
        errors.append("State must be a two-letter abbreviation.")
    if data["zip"] and not re.fullmatch(r"\d{5}(?:-\d{4})?", str(data["zip"])):
        errors.append("ZIP code must contain 5 digits, optionally followed by a 4-digit extension.")
    if not data["acknowledged"]:
        errors.append("You must acknowledge the agreement before submitting.")
    return data, errors


def wrap_text(text: str, font: str, size: float, max_width: float) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if not current or stringWidth(candidate, font, size) <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_wrapped(
    pdf: canvas.Canvas,
    text: str,
    x: float,
    y: float,
    width: float,
    *,
    font: str = "Times-Roman",
    size: float = 10,
    leading: float = 11.5,
) -> float:
    pdf.setFont(font, size)
    for line in wrap_text(text, font, size, width):
        pdf.drawString(x, y, line)
        y -= leading
    return y


def generate_pdf(
    data: dict[str, str | bool],
    submission_id: str,
    submitted_at: datetime,
    agreement_type: str = "nonresident",
) -> bytes:
    profile = agreement_profile(agreement_type)
    form_title = str(profile["form_title"])
    intro = str(profile["intro"])
    items = list(profile["items"])
    output = io.BytesIO()
    pdf = canvas.Canvas(output, pagesize=letter, pageCompression=1)
    width, _ = letter
    blue = HexColor("#0B2F73")

    pdf.setTitle("Sugarwood Key Card Access Agreement")
    pdf.setAuthor("Sugarwood Homeowners Association")

    pdf.setStrokeColor(HexColor("#3974C6"))
    pdf.setLineWidth(0.6)
    pdf.line(78, 742, 534, 742)
    pdf.line(78, 659, 534, 659)

    pdf.setFillColor(blue)
    pdf.setFont("Helvetica-Oblique", 15)
    pdf.drawCentredString(width / 2, 717, "Sugarwood Homeowners Association")
    pdf.setFont("Helvetica-Oblique", 14)
    pdf.drawCentredString(width / 2, 677, "Key Card Access Agreement")

    title_width = stringWidth(form_title, "Times-Roman", 10.5)
    pdf.setFillColor(HexColor("#FFF200"))
    pdf.rect((width - title_width) / 2 - 5, 629, title_width + 10, 15, fill=1, stroke=0)
    pdf.setFillColor(black)
    pdf.setFont("Times-Roman", 10.5)
    pdf.drawCentredString(width / 2, 632, form_title)

    left = 44
    y = 608
    y = draw_wrapped(pdf, intro, left, y, 524, size=9.2, leading=10.5)
    y -= 2
    for number, item in enumerate(items, start=1):
        pdf.setFont("Times-Roman", 9.2)
        pdf.drawRightString(67, y, f"{number}.")
        lines = wrap_text(item, "Times-Roman", 9.2, 492)
        for line in lines:
            pdf.drawString(75, y, line)
            y -= 10.5

    y -= 10
    pdf.setFont("Times-Roman", 10)
    pdf.drawString(left, y, str(profile["address_label"]))
    y -= 24

    def value_line(label: str, value: str, line_width: float = 300) -> None:
        nonlocal y
        pdf.setFont("Times-Roman", 10)
        pdf.drawString(left, y, label)
        label_width = stringWidth(label, "Times-Roman", 10)
        start = left + label_width + 4
        pdf.setStrokeColor(HexColor("#666666"))
        pdf.line(start, y - 1, start + line_width, y - 1)
        pdf.setFont("Helvetica", 9.5)
        pdf.setFillColor(black)
        pdf.drawString(start + 3, y + 1, value[:95])
        y -= 24

    value_line("Street:", str(data["street"]), 310)
    city_state_zip = f'{data["city"]}, {str(data["state"]).upper()} {data["zip"]}'
    value_line("City, State Zip code", city_state_zip, 300)
    value_line("Print Full Name:", str(data["fullName"]), 430)
    value_line("Signature:", str(data["signature"]), 250)
    display_date = submitted_at.astimezone(ZoneInfo("America/New_York")).strftime("%m/%d/%Y")
    value_line("Date:", display_date, 250)
    value_line("Phone Number:", str(data["phone"]), 225)
    value_line("Email:", str(data["email"]), 300)

    y -= 3
    y = draw_wrapped(pdf, RETURN_TEXT, left, y, 524, size=9.5, leading=11)
    y -= 8
    for line in ("SHA Board of Directors", "PO Box 22702", "Knoxville, TN  37933"):
        pdf.drawString(left, y, line)
        y -= 11

    eastern = submitted_at.astimezone(ZoneInfo("America/New_York"))
    pdf.setFillColor(HexColor("#EAF2F8"))
    pdf.roundRect(left, 38, 524, 42, 4, fill=1, stroke=0)
    pdf.setFillColor(blue)
    pdf.setFont("Helvetica-Bold", 8.2)
    pdf.drawString(left + 10, 64, f'Electronically signed by {data["signature"]}')
    pdf.setFillColor(black)
    pdf.setFont("Helvetica", 7.8)
    pdf.drawString(
        left + 10,
        51,
        f"{eastern.strftime('%B %d, %Y at %I:%M:%S %p %Z')}  |  Submission ID: {submission_id}",
    )
    pdf.drawString(left + 10, 41, "Electronic Signature Certificate generated separately.")

    pdf.showPage()
    pdf.save()
    return output.getvalue()


def generate_signature_certificate(
    data: dict[str, str | bool],
    submission_id: str,
    submitted_at: datetime,
    agreement_hash: str,
    agreement_type: str = "nonresident",
) -> bytes:
    profile = agreement_profile(agreement_type)
    output = io.BytesIO()
    pdf = canvas.Canvas(output, pagesize=letter, pageCompression=1)
    width, _ = letter
    blue = HexColor("#102E56")
    accent = HexColor("#D7A933")
    pale = HexColor("#EAF2F8")
    eastern = submitted_at.astimezone(ZoneInfo("America/New_York"))

    pdf.setTitle("Electronic Signature Certificate")
    pdf.setAuthor("Sugarwood Homeowners Association")
    pdf.setFillColor(blue)
    pdf.rect(0, 676, width, 116, fill=1, stroke=0)
    pdf.setFillColor(accent)
    pdf.rect(0, 670, width, 6, fill=1, stroke=0)
    pdf.setFillColor(HexColor("#CADCEC"))
    pdf.setFont("Helvetica-Bold", 8.5)
    pdf.drawString(54, 751, "SUGARWOOD HOMEOWNERS ASSOCIATION")
    pdf.setFillColor(HexColor("#FFFFFF"))
    pdf.setFont("Times-Bold", 22)
    pdf.drawString(54, 716, "Electronic Signature Certificate")
    pdf.setFont("Helvetica", 9.5)
    pdf.drawString(54, 695, "Key Card Access Agreement")

    left, right = 54, 558
    y = 636
    pdf.setFillColor(blue)
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(left, y, "Signature record")
    y -= 20

    rows = [
        ("Submission ID", submission_id),
        ("Signer", str(data["fullName"])),
        ("Typed signature", str(data["signature"])),
        ("Signature method", "Typed electronic signature"),
        ("Submitted (Eastern)", eastern.strftime("%B %d, %Y at %I:%M:%S %p %Z")),
        ("Submitted (UTC)", submitted_at.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")),
        ("Timestamp source", "Backend UTC clock - not supplied by the signer or browser"),
        ("Agreement version", str(profile["agreement_version"])),
        ("Acknowledgment accepted", "Yes" if data["acknowledged"] else "No"),
        ("Identity verification", "No independent identity verification performed"),
    ]
    for index, (label, value) in enumerate(rows):
        if index % 2 == 0:
            pdf.setFillColor(HexColor("#F5F8FA"))
            pdf.rect(left, y - 13, right - left, 22, fill=1, stroke=0)
        pdf.setFillColor(HexColor("#526270"))
        pdf.setFont("Helvetica-Bold", 8.5)
        pdf.drawString(left + 8, y - 4, label.upper())
        pdf.setFillColor(black)
        pdf.setFont("Helvetica", 9)
        pdf.drawString(235, y - 4, value)
        y -= 22

    y -= 15
    pdf.setFillColor(blue)
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(left, y, "Member and document details")
    y -= 19
    address = f'{data["street"]}, {data["city"]}, {str(data["state"]).upper()} {data["zip"]}'
    detail_rows = [
        ("Member address", address),
        ("Primary email", str(data["email"])),
    ]
    if data.get("email2"):
        detail_rows.append(("Optional second email", str(data["email2"])))
    detail_rows.extend(
        [
            ("Phone", str(data["phone"])),
            ("Agreement PDF SHA-256", agreement_hash),
        ]
    )
    for label, value in detail_rows:
        pdf.setFillColor(HexColor("#526270"))
        pdf.setFont("Helvetica-Bold", 8.5)
        pdf.drawString(left, y, label.upper())
        pdf.setFillColor(black)
        font, size = ("Courier", 7.3) if "SHA-256" in label else ("Helvetica", 9)
        pdf.setFont(font, size)
        value_lines = wrap_text(value, font, size, right - 200)
        for line in value_lines:
            pdf.drawString(200, y, line)
            y -= 10
        y -= 8

    y -= 5
    pdf.setFillColor(pale)
    pdf.roundRect(left, y - 81, right - left, 88, 5, fill=1, stroke=0)
    pdf.setFillColor(blue)
    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(left + 12, y - 12, "SIGNER'S ELECTRONIC CONSENT")
    pdf.setFillColor(black)
    y = draw_wrapped(
        pdf,
        SIGNATURE_CONSENT,
        left + 12,
        y - 29,
        right - left - 24,
        font="Helvetica",
        size=8.5,
        leading=11,
    )

    pdf.setFillColor(HexColor("#526270"))
    disclaimer = (
        "This system-generated certificate records the electronic-signature process used for "
        "this submission. It is not a notarization or independent proof of the signer's identity. "
        "Match this certificate to the agreement using the Submission ID shown on both documents."
    )
    draw_wrapped(pdf, disclaimer, left, 68, right - left, font="Helvetica", size=7.8, leading=10)
    pdf.setStrokeColor(HexColor("#D7E0E8"))
    pdf.line(left, 38, right, 38)
    pdf.setFont("Helvetica", 7.5)
    pdf.drawString(left, 25, f"Certificate for submission {submission_id}")
    pdf.drawRightString(right, 25, "Generated with the signed agreement")

    pdf.showPage()
    pdf.save()
    return output.getvalue()


def create_submission_id(
    submitted_at: datetime, agreement_type: str = "nonresident"
) -> str:
    profile = agreement_profile(agreement_type)
    eastern = submitted_at.astimezone(ZoneInfo("America/New_York"))
    return (
        f"{profile['submission_prefix']}-{eastern:%Y%m%d}-"
        f"{secrets.token_hex(3).upper()}"
    )


class PrototypeHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def send_json(self, status: HTTPStatus, payload: object) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if urlparse(self.path).path == "/api/form-config":
            self.send_json(
                HTTPStatus.OK,
                {
                    "formTitle": FORM_TITLE,
                    "intro": INTRO,
                    "agreementItems": AGREEMENT_ITEMS,
                    "signatureConsent": SIGNATURE_CONSENT,
                },
            )
            return
        super().do_GET()

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/submissions":
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 32_768:
                raise ValueError("Request body size is invalid.")
            raw = json.loads(self.rfile.read(length).decode("utf-8"))
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            self.send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "errors": [str(exc)]})
            return

        data, errors = validate_submission(raw)
        if errors:
            self.send_json(HTTPStatus.UNPROCESSABLE_ENTITY, {"ok": False, "errors": errors})
            return

        submitted_at = datetime.now(timezone.utc)
        submission_id = create_submission_id(submitted_at)
        agreement_bytes = generate_pdf(data, submission_id, submitted_at)
        agreement_hash = hashlib.sha256(agreement_bytes).hexdigest().upper()
        certificate_bytes = generate_signature_certificate(
            data, submission_id, submitted_at, agreement_hash
        )
        GENERATED_DIR.mkdir(exist_ok=True)
        agreement_name = f"{submission_id}-agreement.pdf"
        certificate_name = f"{submission_id}-signature-certificate.pdf"
        package_name = f"{submission_id}-signed-documents.zip"
        (GENERATED_DIR / agreement_name).write_bytes(agreement_bytes)
        (GENERATED_DIR / certificate_name).write_bytes(certificate_bytes)

        package = io.BytesIO()
        with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(agreement_name, agreement_bytes)
            archive.writestr(certificate_name, certificate_bytes)
        package_bytes = package.getvalue()
        (GENERATED_DIR / package_name).write_bytes(package_bytes)

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/zip")
        self.send_header("Content-Disposition", f'attachment; filename="{package_name}"')
        self.send_header("Content-Length", str(len(package_bytes)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(package_bytes)

    def log_message(self, format: str, *args: object) -> None:
        print(f"[{self.log_date_time_string()}] {format % args}")


def main() -> None:
    host, port = "127.0.0.1", 8000
    GENERATED_DIR.mkdir(exist_ok=True)
    server = ThreadingHTTPServer((host, port), PrototypeHandler)
    print(f"Sugarwood form prototype running at http://{host}:{port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
