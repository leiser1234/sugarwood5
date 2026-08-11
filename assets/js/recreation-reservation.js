(function () {
  "use strict";
  var form = document.querySelector("[data-reservation-form]");
  if (!form) return;
  var output = document.querySelector("[data-reservation-output]");
  var outputText = document.querySelector("[data-reservation-text]");
  var formStatus = document.querySelector("[data-reservation-status]");
  var outputStatus = document.querySelector("[data-output-status]");
  var printSheet = document.querySelector("[data-print-sheet]");
  var currentText = "";
  var currentHtml = "";

  function value(data, name) { return String(data.get(name) || "Not provided").trim(); }
  function facilities(data) { var items = data.getAll("facility"); return items.length ? items.join(", ") : "None selected"; }
  function escapeHtml(text) { return String(text).replace(/[&<>"']/g, function (character) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[character]; }); }
  function rows(data) {
    return [["Request date", value(data, "requestDate")], ["Event date", value(data, "eventDate")], ["Member name", value(data, "memberName")], ["Phone", value(data, "phone")], ["Address", value(data, "address")], ["Event type", value(data, "eventType")], ["Event time", value(data, "startTime") + " to " + value(data, "endTime")], ["Requested facilities", facilities(data)], ["People age 21 and older", value(data, "adults")], ["Children over age 2", value(data, "childrenOverTwo")], ["Children under age 2", value(data, "childrenUnderTwo")], ["Total swimmers", value(data, "swimmers")], ["Acknowledged by", value(data, "typedName")]];
  }
  function buildText(items) {
    var lines = ["SUGARWOOD HOMEOWNERS ASSOCIATION", "RECREATION AREA RESERVATION REQUEST", "TEST SITE — NOT SUBMITTED OR CONFIRMED", ""];
    items.forEach(function (item) { lines.push(item[0] + ": " + item[1]); });
    lines.push("", "ACKNOWLEDGMENTS", "The member accepted the recreation-area rules and understands this summary does not confirm a reservation.", "", "HOA USE ONLY", "Availability confirmed: ____________________", "Deposit/check information: ____________________", "Board approval: ____________________");
    return lines.join("\n");
  }
  function buildHtml(items) {
    var tableRows = items.map(function (item) { return "<tr><th>" + escapeHtml(item[0]) + "</th><td>" + escapeHtml(item[1]) + "</td></tr>"; }).join("");
    return "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>Sugarwood Recreation Reservation Request</title><style>body{max-width:800px;margin:40px auto;padding:0 24px;color:#173043;font:16px/1.5 Arial,sans-serif}h1{color:#0a2941}aside{padding:12px 16px;background:#fff6df;border-left:4px solid #d99b2b}table{width:100%;border-collapse:collapse;margin:24px 0}th,td{padding:10px;border:1px solid #d9e1e3;text-align:left;vertical-align:top}th{width:34%;background:#f3efe5}h2{margin-top:30px}@media print{body{margin:0;max-width:none}}</style></head><body><h1>Sugarwood Recreation Area Reservation Request</h1><aside><strong>TEST SITE — NOT SUBMITTED OR CONFIRMED</strong></aside><table>" + tableRows + "</table><h2>Acknowledgments</h2><p>The member accepted the recreation-area rules and understands this summary does not confirm a reservation.</p><h2>HOA use only</h2><p>Availability confirmed: ____________________</p><p>Deposit/check information: ____________________</p><p>Board approval: ____________________</p></body></html>";
  }
  function download(contents, filename, type) {
    var url = URL.createObjectURL(new Blob([contents], { type: type }));
    var link = document.createElement("a"); link.href = url; link.download = filename; document.body.appendChild(link); link.click(); link.remove(); URL.revokeObjectURL(url);
  }

  document.querySelector("[data-autofill-reservation]").addEventListener("click", function () {
    var sample = {
      memberName: "Jordan Sample",
      phone: "865-555-0142",
      address: "123 Butternut Circle",
      requestDate: new Date().toISOString().slice(0, 10),
      eventDate: "2026-09-19",
      eventType: "Neighborhood birthday gathering",
      startTime: "14:00",
      endTime: "17:00",
      adults: "12",
      childrenOverTwo: "6",
      childrenUnderTwo: "1",
      swimmers: "14",
      typedName: "Jordan Sample"
    };
    Object.keys(sample).forEach(function (name) { form.elements[name].value = sample[name]; });
    form.querySelectorAll('input[name="facility"]').forEach(function (field) { field.checked = field.value === "Outside Pavilion" || field.value === "Pool" || field.value === "Grill"; });
    form.elements.rulesAccepted.checked = true;
    form.elements.confirmationAccepted.checked = true;
    formStatus.textContent = "Fictional sample information added. Review it or create the request summary.";
    output.hidden = true;
  });

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    if (!form.checkValidity()) { form.reportValidity(); return; }
    if (!form.querySelectorAll('input[name="facility"]:checked').length) { formStatus.textContent = "Select at least one requested facility."; form.querySelector('input[name="facility"]').focus(); return; }
    var items = rows(new FormData(form)); currentText = buildText(items); currentHtml = buildHtml(items); outputText.textContent = currentText; output.hidden = false; formStatus.textContent = "Summary created. Nothing has been submitted or saved."; outputStatus.textContent = ""; output.scrollIntoView({ behavior: "smooth", block: "start" });
  });
  form.addEventListener("reset", function () { output.hidden = true; currentText = ""; currentHtml = ""; formStatus.textContent = ""; outputStatus.textContent = ""; });
  document.querySelector("[data-copy-summary]").addEventListener("click", function () { navigator.clipboard.writeText(currentText).then(function () { outputStatus.textContent = "Summary copied to the clipboard."; }, function () { outputStatus.textContent = "Copy was unavailable. Select the summary text and copy it manually."; }); });
  document.querySelector("[data-download-text]").addEventListener("click", function () { download(currentText, "sugarwood-recreation-request.txt", "text/plain;charset=utf-8"); });
  document.querySelector("[data-download-html]").addEventListener("click", function () { download(currentHtml, "sugarwood-recreation-request.html", "text/html;charset=utf-8"); });
  document.querySelector("[data-print-summary]").addEventListener("click", function () { printSheet.innerHTML = currentHtml.replace(/^.*?<body>/s, "").replace(/<\/body>.*$/s, ""); printSheet.hidden = false; document.body.classList.add("reservation-printing"); window.print(); document.body.classList.remove("reservation-printing"); printSheet.hidden = true; });
})();
