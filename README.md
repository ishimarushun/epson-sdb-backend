# Epson Server Direct Print Backend MVP

Dockerised FastAPI MVP for Epson Server Direct Print. It lets an API client create print jobs, lets an Epson TM-m30II-S poll for jobs, returns Epson Server Direct Print XML when work exists, and returns an empty HTTP 200 XML response when there is no work.

## Run

```bash
cp .env.example .env
docker compose up --build
```

The API will be available at `http://localhost:8000`.

For local development without Docker:

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Environment

- `API_KEY`: shared API key required by `/api/*` endpoints.
- `PRINTER_POLL_PASSWORD`: shared HTTP Digest password required by Epson Server Direct Print polling. Configure the printer's Server Direct Print ID as the printer ID, and configure this value as its password.
- `PRINTER_POLL_REALM`: optional HTTP Digest realm for printer polling. Defaults to `epson-sdp`.
- `DATABASE_URL`: SQLAlchemy database URL. Defaults to SQLite.
- `DEFAULT_DEVICE_ID`: Epson ePOS device id used in returned SDP XML. Defaults to `local_printer`.
- `PRINTER_WIDTH_DOTS`: printable raster width for image jobs. Defaults to `576`, the common 80mm / 203dpi printable width for TM-m30II-class printers.

## Endpoints

### Health

```bash
curl http://localhost:8000/health
```

### Admin Test Page

Open `http://localhost:8000/admin` in a browser.

### Create A Print Job

```bash
curl -X POST http://localhost:8000/api/jobs \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-secret" \
  -d '{
    "printer_id": "printer_001",
    "type": "text",
    "text": "Hello from cloud",
    "copies": 1
  }'
```

### Create An Image Print Job

Image jobs accept a raw base64 image string or a `data:image/...;base64,...` value. The backend validates the image immediately, then the printer poll converts it to monochrome raster data for 80mm paper at 203dpi. Images wider than `PRINTER_WIDTH_DOTS` are resized proportionally to 576 dots by default; narrower images keep their width and are padded to a multiple of 8 dots for raster packing.

```bash
IMAGE_BASE64="$(base64 -w 0 receipt-logo.png)"

curl -X POST http://localhost:8000/api/jobs \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-secret" \
  -d "{
    \"printer_id\": \"printer_001\",
    \"type\": \"image\",
    \"image_base64\": \"${IMAGE_BASE64}\",
    \"copies\": 1
  }"
```

On Windows PowerShell:

```powershell
$imageBase64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes("receipt-logo.png"))

Invoke-RestMethod http://localhost:8000/api/jobs `
  -Method Post `
  -Headers @{ "X-API-Key" = "dev-secret" } `
  -ContentType "application/json" `
  -Body (@{
    printer_id = "printer_001"
    type = "image"
    image_base64 = $imageBase64
    copies = 1
  } | ConvertTo-Json)
```

### List Recent Jobs

```bash
curl http://localhost:8000/api/jobs \
  -H "X-API-Key: dev-secret"
```

### Epson GetRequest Poll

When no pending job exists, this returns HTTP 200 with `Content-Type: text/xml; charset=utf-8` and an empty body.

```bash
curl -i -X POST http://localhost:8000/sdp/print \
  --digest -u printer_001:dev-printer-secret \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data "ConnectionType=GetRequest&ID=printer_001"
```

When a pending job exists, the server marks it `sent_to_printer` and returns:

```xml
<PrintRequestInfo>
  <ePOSPrint>
    <Parameter>
      <devid>local_printer</devid>
      <timeout>10000</timeout>
    </Parameter>
    <PrintData>
      <epos-print xmlns="http://www.epson-pos.com/schemas/2011/03/epos-print">
        ...
      </epos-print>
    </PrintData>
  </ePOSPrint>
</PrintRequestInfo>
```

For image jobs, `<PrintData>` contains a monochrome raster image element:

```xml
<epos-print xmlns="http://www.epson-pos.com/schemas/2011/03/epos-print">
  <image width="576" height="..." color="color_1" mode="mono">...</image>
  <feed line="3" />
  <cut />
</epos-print>
```

### Epson SetResponse

Stores the raw printer response XML against the latest sent job. If the response looks like an error, the job is marked `error`; otherwise it is marked `printed`.

```bash
curl -i -X POST http://localhost:8000/sdp/print \
  --digest -u printer_001:dev-printer-secret \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "ConnectionType=SetResponse" \
  --data-urlencode "ID=printer_001" \
  --data-urlencode "ResponseFile=<response success=\"true\" />"
```

## Tests

```bash
cd backend
pytest
```
