# Sugarwood HOA Static Website

This folder contains a complete static rebuild of the public Sugarwood HOA website. It uses plain HTML, one CSS file, and one small JavaScript file. There is no WordPress, PHP, database, Node.js, or production build step.

## Preview

From `S:\sugarwood`, run:

```powershell
python -m http.server 8080
```

Then open <http://127.0.0.1:8080/>. Most pages also work when their `index.html` files are opened directly.

## Common updates

- Page content: edit the relevant `index.html` file in its route folder.
- Colors and layout: edit `assets/css/site.css`.
- Mobile navigation and contact-form routing: edit `assets/js/site.js`.
- Documents: add the file to `assets/documents/` and update the page link.
- Images: add the file to `assets/images/` and use a relative path from the page.
- Board roster: update `contact/index.html` only after confirming names, roles, phones, and terms.
- Pool schedule: update `pool-hours/index.html` only after confirming the published dates and hours.

The audit and source traceability files are at the repository root. Re-run `work/build_site.py` only if you intend to regenerate the pages from that script; direct HTML edits are otherwise fine.

## Publishing scope

For a production upload, publish the site pages and `assets/` folder. Keep `work/`, `source-archive/`, `screenshots/`, and the audit Markdown files as local project records unless the chosen hosting workflow explicitly excludes them from public browsing.
