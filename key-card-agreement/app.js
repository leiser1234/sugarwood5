const form = document.querySelector("#agreement-form");
const statusBox = document.querySelector("#agreement-status");
const submitButton = document.querySelector("#agreement-submit");
const apiBase = String(window.SUGARWOOD_KEY_CARD_API || "").replace(/\/$/, "");

function showStatus(message, type) {
  statusBox.textContent = message;
  statusBox.className = `keycard-status keycard-status--${type}`;
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

if (!apiBase) {
  submitButton.disabled = true;
  showStatus(
    "The online agreement is published for review. Document submission will open after the secure Azure service is connected.",
    "notice",
  );
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!apiBase || !form.reportValidity()) return;

  const fields = new FormData(form);
  const payload = Object.fromEntries(fields.entries());
  payload.acknowledged = fields.get("acknowledged") === "on";

  submitButton.disabled = true;
  submitButton.textContent = "Creating documents...";
  showStatus("Creating your signed document package...", "notice");

  try {
    const response = await fetch(`${apiBase}/api/submissions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.errors?.join(" ") || "The signed documents could not be created.");
    }

    const disposition = response.headers.get("Content-Disposition") || "";
    const filename = disposition.match(/filename="([^"]+)"/)?.[1] || "signed-key-card-agreement.zip";
    downloadBlob(await response.blob(), filename);
    showStatus("Your agreement and Electronic Signature Certificate were created and downloaded.", "success");
    form.reset();
  } catch (error) {
    showStatus(error.message, "error");
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = "Create signed document package";
  }
});
