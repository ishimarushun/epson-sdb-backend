import base64
import hashlib
import io
import os
import tempfile

os.environ["API_KEY"] = "test-key"
os.environ["PRINTER_POLL_PASSWORD"] = "test-printer-secret"
db_file = tempfile.NamedTemporaryFile(delete=False)
db_file.close()
os.environ["DATABASE_URL"] = f"sqlite:///{db_file.name}"
os.environ["DEFAULT_DEVICE_ID"] = "local_printer"

from fastapi.testclient import TestClient  # noqa: E402
from httpx import DigestAuth  # noqa: E402
from PIL import Image  # noqa: E402
import pytest  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture()
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_requires_key(client: TestClient) -> None:
    response = client.get("/api/jobs")
    assert response.status_code == 401


def test_admin_page_shows_jobs_endpoint_and_request_errors(client: TestClient) -> None:
    response = client.get("/admin")

    assert response.status_code == 200
    assert 'new URL("api/jobs", new URL("./", window.location.href))' in response.text
    assert "Request failed before the server responded" in response.text


def test_printer_poll_requires_digest_auth(client: TestClient) -> None:
    response = client.post(
        "/sdp/print",
        data={"ConnectionType": "GetRequest", "ID": "printer_001"},
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"].startswith("Digest ")


def test_printer_poll_rejects_auth_username_that_does_not_match_id(client: TestClient) -> None:
    response = client.post(
        "/sdp/print",
        auth=_printer_auth("printer_a"),
        data={"ConnectionType": "GetRequest", "ID": "printer_b"},
    )

    assert response.status_code == 403


def test_printer_poll_accepts_absolute_digest_uri(client: TestClient) -> None:
    initial_response = client.post(
        "/sdp/print",
        data={"ConnectionType": "GetRequest", "ID": "printer_absolute_uri"},
    )
    assert initial_response.status_code == 401

    response = client.post(
        "/sdp/print",
        headers={
            "Authorization": _digest_authorization_header(
                initial_response.headers["www-authenticate"],
                username="printer_absolute_uri",
                password="test-printer-secret",
                method="POST",
                uri="http://testserver/sdp/print",
            )
        },
        data={"ConnectionType": "GetRequest", "ID": "printer_absolute_uri"},
    )

    assert response.status_code == 200
    assert response.content == b""


def test_create_job_and_list_jobs(client: TestClient) -> None:
    response = client.post(
        "/api/jobs",
        headers={"X-API-Key": "test-key"},
        json={
            "printer_id": "printer_001",
            "type": "text",
            "text": "Hello from cloud",
            "copies": 1,
        },
    )
    assert response.status_code == 201
    assert response.json()["status"] == "pending"

    list_response = client.get("/api/jobs", headers={"X-API-Key": "test-key"})
    assert list_response.status_code == 200
    assert any(job["text"] == "Hello from cloud" for job in list_response.json())


def test_get_request_returns_empty_xml_when_no_job(client: TestClient) -> None:
    response = client.post(
        "/sdp/print",
        auth=_printer_auth("unknown_printer"),
        data={"ConnectionType": "GetRequest", "ID": "unknown_printer"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/xml; charset=utf-8"
    assert response.content == b""


def test_get_request_returns_sdp_xml_and_marks_sent(client: TestClient) -> None:
    create_response = client.post(
        "/api/jobs",
        headers={"X-API-Key": "test-key"},
        json={
            "printer_id": "printer_poll_xml",
            "type": "text",
            "text": "Print me",
            "copies": 1,
        },
    )
    assert create_response.status_code == 201

    poll_response = client.post(
        "/sdp/print",
        auth=_printer_auth("printer_poll_xml"),
        data={"ConnectionType": "GetRequest", "ID": "printer_poll_xml"},
    )

    assert poll_response.status_code == 200
    assert poll_response.headers["content-type"] == "text/xml; charset=utf-8"
    assert "<PrintRequestInfo>" in poll_response.text
    assert "<devid>local_printer</devid>" in poll_response.text
    assert "<epos-print xmlns=\"http://www.epson-pos.com/schemas/2011/03/epos-print\">" in poll_response.text
    assert "<text>Print me</text>" in poll_response.text

    jobs_response = client.get("/api/jobs", headers={"X-API-Key": "test-key"})
    job = next(job for job in jobs_response.json() if job["printer_id"] == "printer_poll_xml")
    assert job["status"] == "sent_to_printer"


def test_image_job_returns_80mm_203dpi_raster_xml(client: TestClient) -> None:
    image_base64 = _make_png_base64(width=800, height=100)
    create_response = client.post(
        "/api/jobs",
        headers={"X-API-Key": "test-key"},
        json={
            "printer_id": "printer_image",
            "type": "image",
            "image_base64": image_base64,
            "copies": 1,
        },
    )
    assert create_response.status_code == 201
    assert create_response.json()["type"] == "image"

    poll_response = client.post(
        "/sdp/print",
        auth=_printer_auth("printer_image"),
        data={"ConnectionType": "GetRequest", "ID": "printer_image"},
    )

    assert poll_response.status_code == 200
    assert "<image width=\"576\" height=\"72\" color=\"color_1\" mode=\"mono\">" in poll_response.text
    assert "<cut />" in poll_response.text


def test_image_job_rejects_invalid_base64(client: TestClient) -> None:
    response = client.post(
        "/api/jobs",
        headers={"X-API-Key": "test-key"},
        json={
            "printer_id": "printer_bad_image",
            "type": "image",
            "image_base64": "not-an-image",
            "copies": 1,
        },
    )
    assert response.status_code == 400


def test_set_response_marks_latest_sent_job_printed(client: TestClient) -> None:
    client.post(
        "/api/jobs",
        headers={"X-API-Key": "test-key"},
        json={
            "printer_id": "printer_set_response",
            "type": "text",
            "text": "Complete me",
            "copies": 1,
        },
    )
    client.post(
        "/sdp/print",
        auth=_printer_auth("printer_set_response"),
        data={"ConnectionType": "GetRequest", "ID": "printer_set_response"},
    )

    response = client.post(
        "/sdp/print",
        auth=_printer_auth("printer_set_response"),
        data={
            "ConnectionType": "SetResponse",
            "ID": "printer_set_response",
            "ResponseFile": "<response success=\"true\" />",
        },
    )

    assert response.status_code == 200
    assert response.content == b""

    jobs_response = client.get("/api/jobs", headers={"X-API-Key": "test-key"})
    job = next(job for job in jobs_response.json() if job["printer_id"] == "printer_set_response")
    assert job["status"] == "printed"
    assert job["printer_response"] == "<response success=\"true\" />"


def _printer_auth(printer_id: str) -> DigestAuth:
    return DigestAuth(printer_id, "test-printer-secret")


def _digest_authorization_header(
    challenge: str,
    username: str,
    password: str,
    method: str,
    uri: str,
) -> str:
    challenge_fields = _parse_digest_challenge(challenge)
    realm = challenge_fields["realm"]
    nonce = challenge_fields["nonce"]
    qop = "auth"
    nc = "00000001"
    cnonce = "test-cnonce"
    ha1 = _md5_hex(f"{username}:{realm}:{password}")
    ha2 = _md5_hex(f"{method}:{uri}")
    response = _md5_hex(f"{ha1}:{nonce}:{nc}:{cnonce}:{qop}:{ha2}")
    return (
        f'Digest username="{username}", realm="{realm}", nonce="{nonce}", '
        f'uri="{uri}", response="{response}", algorithm=MD5, '
        f'qop={qop}, nc={nc}, cnonce="{cnonce}"'
    )


def _parse_digest_challenge(challenge: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for item in challenge.removeprefix("Digest ").split(","):
        key, value = item.strip().split("=", 1)
        fields[key] = value.strip('"')
    return fields


def _md5_hex(value: str) -> str:
    return hashlib.md5(value.encode("utf-8")).hexdigest()


def _make_png_base64(width: int, height: int) -> str:
    image = Image.new("RGB", (width, height), "white")
    for x in range(0, width, 20):
        for y in range(height):
            image.putpixel((x, y), (0, 0, 0))
    output = io.BytesIO()
    image.save(output, format="PNG")
    return base64.b64encode(output.getvalue()).decode("ascii")
