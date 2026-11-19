# Sugarwood HOA Forms API

Azure Functions (Python 3.12) backend for the website's signed forms.

## Key-card submission flow

The Function App supports both the non-resident/associate-member agreement and
the resident agreement. Each agreement has its own public website page and HTTP
submission route while sharing validation, PDF generation, signature
certificates, and email delivery.

1. Validate the public form submission.
2. Generate the signed agreement and Electronic Signature Certificate in memory.
3. Send both PDFs as separate attachments through Microsoft Graph using the Function App's system-assigned managed identity.
4. Save the message in `sugarwoodboard@sugarwood.org` Sent Items.
5. Discard the in-memory PDFs when the request ends. The Function App does not persist submission documents in Azure storage.

The Azure storage account attached to the Function App is still required for the Functions runtime and deployment package.

## Required Azure configuration

- System-assigned managed identity enabled.
- Exchange Online Application RBAC role `Application Mail.Send`, scoped to `sugarwoodboard@sugarwood.org`.
- Optional app setting `SENDER_MAILBOX` (defaults to `sugarwoodboard@sugarwood.org`).
- Optional comma-separated app setting `ALLOWED_ORIGINS` for staging origins. Production Sugarwood origins and local port 8080 are included by default.

## Deploy

Package the four runtime files at the ZIP root and request a remote Python build:

```powershell
az functionapp deployment source config-zip `
  --subscription 3d0fc7e4-dd2b-4a11-a8dd-6c40cae76574 `
  --resource-group rg-sugarwood-forms `
  --name sugarwood-hoa-forms-api `
  --src sugarwood-hoa-forms-api.zip `
  --build-remote true
```

Current HTTP routes:

- `GET /api/form-config`
- `POST /api/submissions`
- `GET /api/resident-form-config`
- `POST /api/resident-submissions`
