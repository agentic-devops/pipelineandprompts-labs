from unittest.mock import patch

from tests.conftest import API_HEADERS


class TestHealthEndpoint:
    """Test /health endpoint (unauthenticated)."""

    @patch("app.main.chroma_client")
    def test_returns_healthy_when_vector_store_reachable(self, mock_chroma, client):
        mock_chroma.heartbeat.return_value = 123456789

        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {
            "status": "healthy",
            "vector_store": "reachable",
        }

    @patch("app.main.chroma_client")
    def test_returns_503_when_vector_store_unreachable(self, mock_chroma, client):
        mock_chroma.heartbeat.side_effect = Exception("Connection failed")

        response = client.get("/health")

        assert response.status_code == 503
        assert "unreachable" in response.json()["detail"]


class TestIngestEndpoint:
    """Test /ingest endpoint (requires X-API-Key)."""

    def test_rejects_missing_api_key(self, client):
        response = client.post("/ingest")
        assert response.status_code == 401

    @patch("app.main.ingest_runbooks")
    def test_ingests_runbooks_successfully(self, mock_ingest, client):
        mock_ingest.return_value = {
            "status": "ingested",
            "chunks_ingested": 10,
            "runbooks_processed": 2,
        }

        response = client.post("/ingest", headers=API_HEADERS)

        assert response.status_code == 200
        assert response.json()["status"] == "ingested"
        assert response.json()["chunks_ingested"] == 10

    @patch("app.main.ingest_runbooks")
    def test_handles_ingestion_errors(self, mock_ingest, client):
        mock_ingest.side_effect = Exception("Ingestion failed")

        response = client.post("/ingest", headers=API_HEADERS)

        assert response.status_code == 500
        assert "Ingestion failed" in response.json()["detail"]


class TestQueryEndpoint:
    """Test /query endpoint (requires X-API-Key)."""

    def test_rejects_missing_api_key(self, client):
        response = client.post("/query", json={"question": "test"})
        assert response.status_code == 401

    @patch("app.main.query_runbooks")
    def test_queries_runbooks_successfully(self, mock_query, client):
        mock_query.return_value = {
            "answer": "Restart the service",
            "sources": ["troubleshooting.md"],
        }

        response = client.post(
            "/query",
            headers=API_HEADERS,
            json={"question": "how to fix the service?"},
        )

        assert response.status_code == 200
        assert response.json()["answer"] == "Restart the service"
        assert "troubleshooting.md" in response.json()["sources"]

    def test_rejects_empty_question(self, client):
        response = client.post(
            "/query",
            headers=API_HEADERS,
            json={"question": ""},
        )

        assert response.status_code == 400
        assert "cannot be empty" in response.json()["detail"]

    def test_rejects_whitespace_only_question(self, client):
        response = client.post(
            "/query",
            headers=API_HEADERS,
            json={"question": "   "},
        )

        assert response.status_code == 400
        assert "cannot be empty" in response.json()["detail"]

    def test_rejects_too_long_question(self, client):
        response = client.post(
            "/query",
            headers=API_HEADERS,
            json={"question": "a" * 2001},
        )

        assert response.status_code == 400
        assert "exceeds maximum length" in response.json()["detail"]

    @patch("app.main.query_runbooks")
    def test_handles_query_errors(self, mock_query, client):
        mock_query.side_effect = Exception("Query failed")

        response = client.post(
            "/query",
            headers=API_HEADERS,
            json={"question": "test question"},
        )

        assert response.status_code == 500
        assert "Query failed" in response.json()["detail"]

    @patch("app.main.query_runbooks")
    def test_accepts_valid_question_length(self, mock_query, client):
        mock_query.return_value = {"answer": "Answer", "sources": []}

        response = client.post(
            "/query",
            headers=API_HEADERS,
            json={"question": "a" * 2000},
        )

        assert response.status_code == 200
