from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from app.db import init_db
from app.routes_api import router as api_router
from app.routes_sdp import router as sdp_router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


app = FastAPI(title="Epson SDP Backend", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/admin", response_class=HTMLResponse)
def admin_page() -> str:
    return """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Epson SDP Test</title>
    <style>
      body { font-family: system-ui, sans-serif; max-width: 760px; margin: 40px auto; padding: 0 16px; }
      label { display: block; margin: 14px 0 6px; font-weight: 600; }
      input, textarea, button { width: 100%; box-sizing: border-box; padding: 10px; font: inherit; }
      button { margin-top: 16px; cursor: pointer; }
      pre { background: #f4f4f4; padding: 12px; overflow: auto; }
    </style>
  </head>
  <body>
    <h1>Epson SDP Test</h1>
    <form id="job-form">
      <label>API key</label>
      <input id="api-key" value="dev-secret">
      <label>Printer ID</label>
      <input id="printer-id" value="printer_001">
      <label>Text</label>
      <textarea id="text" rows="4">Hello from cloud</textarea>
      <label>Copies</label>
      <input id="copies" type="number" min="1" max="10" value="1">
      <button type="submit">Create print job</button>
    </form>
    <pre id="result"></pre>
    <script>
      const form = document.getElementById("job-form");
      const result = document.getElementById("result");
      const jobsUrl = new URL("api/jobs", new URL("./", window.location.href));

      result.textContent = `Ready. Jobs endpoint: ${jobsUrl}`;

      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        result.textContent = `Submitting to ${jobsUrl} ...`;

        try {
          const response = await fetch(jobsUrl, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-API-Key": document.getElementById("api-key").value
            },
            body: JSON.stringify({
              printer_id: document.getElementById("printer-id").value,
              type: "text",
              text: document.getElementById("text").value,
              copies: Number(document.getElementById("copies").value)
            })
          });

          const responseText = await response.text();
          let body = responseText;
          try {
            body = JSON.stringify(JSON.parse(responseText), null, 2);
          } catch {
            body = responseText || "(empty response)";
          }

          result.textContent = `HTTP ${response.status} ${response.statusText}\n\n${body}`;
        } catch (error) {
          result.textContent = `Request failed before the server responded:\n${error}`;
        }
      });
    </script>
  </body>
</html>
"""


app.include_router(api_router)
app.include_router(sdp_router)
