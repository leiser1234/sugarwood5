"""Sugarwood HOA forms API.

Generates the signed key-card agreement and signature certificate in memory,
then sends both PDFs through Microsoft Graph using the Function App's managed
identity. Submission documents are not written to Azure storage.
"""

from __future__ import annotations

import base64
import hashlib
import html
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import azure.functions as func


app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

SENDER_MAILBOX = os.getenv("SENDER_MAILBOX", "sugarwoodboard@sugarwood.org")
DEFAULT_ORIGINS = {
    "https://sugarwood.org",
    "https://www.sugarwood.org",
    "http://127.0.0.1:8080",
    "http://localhost:8080",
}


def allowed_origins() -> set[str]:
    configured = {
        item.strip().rstrip("/")
        for item in os.getenv("ALLOWED_ORIGINS", "").split(",")
        if item.strip()
    }
    return DEFAULT_ORIGINS | configured


def cors_headers(request: func.HttpRequest) -> dict[str, str]:
    origin = (request.headers.get("Origin") or "").rstrip("/")
    headers = {
        "Cache-Control": "no-store",
        "Vary": "Origin",
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
    }
    if origin in allowed_origins():
        headers["Access-Control-Allow-Origin"] = origin
    return headers


def json_response(
    request: func.HttpRequest, payload: object, status_code: int = 200
) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps(payload),
        status_code=status_code,
        mimetype="application/json",
        charset="utf-8",
        headers=cors_headers(request),
    )


def email_recipient(address: str) -> dict[str, dict[str, str]]:
    return {"emailAddress": {"address": address}}


def pdf_attachment(filename: str, content: bytes) -> dict[str, str]:
    return {
        "@odata.type": "#microsoft.graph.fileAttachment",
        "name": filename,
        "contentType": "application/pdf",
        "contentBytes": base64.b64encode(content).decode("ascii"),
    }


def send_documents(
    data: dict[str, str | bool],
    submission_id: str,
    submitted_at: datetime,
    agreement_name: str,
    agreement_bytes: bytes,
    certificate_name: str,
    certificate_bytes: bytes,
    agreement_type: str = "nonresident",
) -> None:
    # Keep non-runtime imports out of module startup so Azure can always index
    # the HTTP functions before loading optional application dependencies.
    from azure.identity import ManagedIdentityCredential

    primary_email = str(data["email"])
    recipients = [email_recipient(SENDER_MAILBOX), email_recipient(primary_email)]
    secondary_email = str(data.get("email2") or "")
    if secondary_email and secondary_email.casefold() not in {
        SENDER_MAILBOX.casefold(),
        primary_email.casefold(),
    }:
        recipients.append(email_recipient(secondary_email))

    eastern_label = submitted_at.astimezone(ZoneInfo("America/New_York")).strftime(
        "%B %d, %Y at %I:%M:%S %p %Z"
    )
    signer = html.escape(str(data["fullName"]))
    if agreement_type == "resident":
        subject = f"Sugarwood resident key-card agreement — {data['fullName']} — {submission_id}"
        document_description = "signed Sugarwood Resident Key Card Access Agreement"
    else:
        subject = f"Sugarwood key-card agreement — {data['fullName']} — {submission_id}"
        document_description = "signed Sugarwood Key Card Access Agreement"
    message_html = (
        f"<p>The {html.escape(document_description)} for <strong>{signer}</strong> "
        "is attached, along with its Electronic Signature Certificate.</p>"
        f"<p><strong>Submission ID:</strong> {html.escape(submission_id)}<br>"
        f"<strong>Received:</strong> {html.escape(eastern_label)}</p>"
        "<p>Please retain both PDF attachments together. No separate copy is stored "
        "in Azure; the email record is the HOA copy.</p>"
    )
    graph_payload = {
        "message": {
            "subject": subject,
            "body": {"contentType": "HTML", "content": message_html},
            "toRecipients": recipients,
            "replyTo": [email_recipient(primary_email)],
            "attachments": [
                pdf_attachment(agreement_name, agreement_bytes),
                pdf_attachment(certificate_name, certificate_bytes),
            ],
        },
        "saveToSentItems": True,
    }

    token = ManagedIdentityCredential().get_token(
        "https://graph.microsoft.com/.default"
    ).token
    endpoint = (
        "https://graph.microsoft.com/v1.0/users/"
        f"{urllib.parse.quote(SENDER_MAILBOX)}/sendMail"
    )
    graph_request = urllib.request.Request(
        endpoint,
        data=json.dumps(graph_payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(graph_request, timeout=30) as response:
        if response.status != 202:
            raise RuntimeError(f"Microsoft Graph returned HTTP {response.status}.")


@app.route(route="form-config", methods=["GET"], trigger_arg_name="request")
def form_config(request: func.HttpRequest) -> func.HttpResponse:
    from server import AGREEMENT_ITEMS, FORM_TITLE, INTRO, SIGNATURE_CONSENT

    return json_response(
        request,
        {
            "formTitle": FORM_TITLE,
            "intro": INTRO,
            "agreementItems": AGREEMENT_ITEMS,
            "signatureConsent": SIGNATURE_CONSENT,
        },
    )


@app.route(
    route="resident-form-config", methods=["GET"], trigger_arg_name="request"
)
def resident_form_config(request: func.HttpRequest) -> func.HttpResponse:
    from server import SIGNATURE_CONSENT, agreement_profile

    profile = agreement_profile("resident")
    return json_response(
        request,
        {
            "formTitle": profile["form_title"],
            "intro": profile["intro"],
            "agreementItems": profile["items"],
            "signatureConsent": SIGNATURE_CONSENT,
        },
    )


def handle_submission(
    request: func.HttpRequest, agreement_type: str
) -> func.HttpResponse:
    if request.method == "OPTIONS":
        return func.HttpResponse(status_code=204, headers=cors_headers(request))

    from server import (
        create_submission_id,
        generate_pdf,
        generate_signature_certificate,
        validate_submission,
    )

    origin = (request.headers.get("Origin") or "").rstrip("/")
    if origin and origin not in allowed_origins():
        return json_response(request, {"ok": False, "errors": ["Origin is not allowed."]}, 403)

    body = request.get_body()
    if not body or len(body) > 32_768:
        return json_response(
            request, {"ok": False, "errors": ["Request body size is invalid."]}, 400
        )

    try:
        raw = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return json_response(
            request, {"ok": False, "errors": ["Request body is not valid JSON."]}, 400
        )

    data, errors = validate_submission(raw)
    if errors:
        return json_response(request, {"ok": False, "errors": errors}, 422)

    submitted_at = datetime.now(timezone.utc)
    submission_id = create_submission_id(submitted_at, agreement_type)
    agreement_bytes = generate_pdf(data, submission_id, submitted_at, agreement_type)
    agreement_hash = hashlib.sha256(agreement_bytes).hexdigest().upper()
    certificate_bytes = generate_signature_certificate(
        data, submission_id, submitted_at, agreement_hash, agreement_type
    )
    agreement_label = "resident-agreement" if agreement_type == "resident" else "agreement"
    agreement_name = f"{submission_id}-{agreement_label}.pdf"
    certificate_name = f"{submission_id}-signature-certificate.pdf"

    try:
        send_documents(
            data,
            submission_id,
            submitted_at,
            agreement_name,
            agreement_bytes,
            certificate_name,
            certificate_bytes,
            agreement_type,
        )
    except Exception as exc:
        # Azure Application Insights receives the exception without exposing
        # credentials or service details to the person submitting the form.
        import logging

        logging.exception("Key-card email delivery failed: %s", exc)
        return json_response(
            request,
            {
                "ok": False,
                "errors": [
                    "The documents were created, but email delivery failed. Please try again shortly."
                ],
            },
            502,
        )

    return json_response(
        request,
        {
            "ok": True,
            "submissionId": submission_id,
            "message": "The signed agreement and signature certificate were emailed successfully.",
        },
        201,
    )


@app.route(
    route="submissions",
    methods=["POST", "OPTIONS"],
    trigger_arg_name="request",
)
def create_submission(request: func.HttpRequest) -> func.HttpResponse:
    return handle_submission(request, "nonresident")


@app.route(
    route="resident-submissions",
    methods=["POST", "OPTIONS"],
    trigger_arg_name="request",
)
def create_resident_submission(request: func.HttpRequest) -> func.HttpResponse:
    return handle_submission(request, "resident")
