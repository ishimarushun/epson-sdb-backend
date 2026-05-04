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
- `DATABASE_URL`: SQLAlchemy database URL. Defaults to SQLite.
- `DEFAULT_DEVICE_ID`: Epson ePOS device id used in returned SDP XML. Defaults to `local_printer`.

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

### List Recent Jobs

```bash
curl http://localhost:8000/api/jobs \
  -H "X-API-Key: dev-secret"
```

### Epson GetRequest Poll

When no pending job exists, this returns HTTP 200 with `Content-Type: text/xml; charset=utf-8` and an empty body.

```bash
curl -i -X POST http://localhost:8000/sdp/print \
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

### Epson SetResponse

Stores the raw printer response XML against the latest sent job. If the response looks like an error, the job is marked `error`; otherwise it is marked `printed`.

```bash
curl -i -X POST http://localhost:8000/sdp/print \
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
