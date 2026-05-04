import os
import tempfile

os.environ["API_KEY"] = "test-key"
db_file = tempfile.NamedTemporaryFile(delete=False)
db_file.close()
os.environ["DATABASE_URL"] = f"sqlite:///{db_file.name}"
os.environ["DEFAULT_DEVICE_ID"] = "local_printer"

from fastapi.testclient import TestClient  # noqa: E402
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
        data={"ConnectionType": "GetRequest", "ID": "printer_set_response"},
    )

    response = client.post(
        "/sdp/print",
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
