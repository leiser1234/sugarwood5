const form = document.querySelector("#agreement-form");
const statusBox = document.querySelector("#agreement-status");
const submitButton = document.querySelector("#agreement-submit");
const apiBase = String(window.SUGARWOOD_KEY_CARD_API || "").replace(/\/$/, "");

function showStatus(message, type) {
  statusBox.textContent = message;
  statusBox.className = `keycard-status keycard-status--${type}`;
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
  submitButton.textContent = "Submitting...";
  showStatus("Creating and emailing your signed documents...", "notice");

  try {
    const response = await fetch(`${apiBase}/api/resident-submissions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.errors?.join(" ") || "The signed documents could not be created.");
    }

    const result = await response.json();
    showStatus(
      `Your agreement and Electronic Signature Certificate were emailed successfully. Submission ID: ${result.submissionId}`,
      "success",
    );
    form.reset();
  } catch (error) {
    showStatus(error.message, "error");
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = "Submit signed agreement";
  }
});
