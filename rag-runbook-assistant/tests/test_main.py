import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
from app.main import app

client = TestClient(app)


class TestHealthEndpoint:
    """Test /health endpoint."""

    @patch('app.main.chroma_client')
    def test_returns_healthy_when_vector_store_reachable(self, mock_chroma):
        """Should return 200 when Chroma is reachable."""
        mock_chroma.heartbeat.return_value = 123456789

        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {
            "status": "healthy",
            "vector_store": "reachable"
        }

    @patch('app.main.chroma_client')
    def test_returns_503_when_vector_store_unreachable(self, mock_chroma):
        """Should return 503 when Chroma fails."""
        mock_chroma.heartbeat.side_effect = Exception("Connection failed")

        response = client.get("/health")

        assert response.status_code == 503
        assert "unreachable" in response.json()["detail"]


class TestIngestEndpoint:
    """Test /ingest endpoint."""

    @patch('app.main.ingest_runbooks')
    def test_ingests_runbooks_successfully(self, mock_ingest):
        """Should call ingest function and return results."""
        mock_ingest.return_value = {
            "status": "ingested",
            "chunks_ingested": 10,
            "runbooks_processed": 2
        }

        response = client.post("/ingest")

        assert response.status_code == 200
        assert response.json()["status"] == "ingested"
        assert response.json()["chunks_ingested"] == 10

    @patch('app.main.ingest_runbooks')
    def test_handles_ingestion_errors(self, mock_ingest):
        """Should return 500 on ingestion failure."""
        mock_ingest.side_effect = Exception("Ingestion failed")

        response = client.post("/ingest")

        assert response.status_code == 500
        assert "Ingestion failed" in response.json()["detail"]


class TestQueryEndpoint:
    """Test /query endpoint."""

    @patch('app.main.query_runbooks')
    def test_queries_runbooks_successfully(self, mock_query):
        """Should accept question and return answer with sources."""
        mock_query.return_value = {
            "answer": "Restart the service",
            "sources": ["troubleshooting.md"]
        }

        response = client.post(
            "/query",
            json={"question": "how to fix the service?"}
        )

        assert response.status_code == 200
        assert response.json()["answer"] == "Restart the service"
        assert "troubleshooting.md" in response.json()["sources"]

    def test_rejects_empty_question(self):
        """Should return 400 for empty question."""
        response = client.post("/query", json={"question": ""})

        assert response.status_code == 400
        assert "cannot be empty" in response.json()["detail"]

    def test_rejects_whitespace_only_question(self):
        """Should return 400 for whitespace-only question."""
        response = client.post("/query", json={"question": "   "})

        assert response.status_code == 400
        assert "cannot be empty" in response.json()["detail"]

    def test_rejects_too_long_question(self):
        """Should return 400 for questions exceeding max length."""
        long_question = "a" * 2001

        response = client.post("/query", json={"question": long_question})

        assert response.status_code == 400
        assert "exceeds maximum length" in response.json()["detail"]

    @patch('app.main.query_runbooks')
    def test_handles_query_errors(self, mock_query):
        """Should return 500 on query failure."""
        mock_query.side_effect = Exception("Query failed")

        response = client.post(
            "/query",
            json={"question": "test question"}
        )

        assert response.status_code == 500
        assert "Query failed" in response.json()["detail"]

    @patch('app.main.query_runbooks')
    def test_accepts_valid_question_length(self, mock_query):
        """Should accept questions up to 2000 characters."""
        mock_query.return_value = {"answer": "Answer", "sources": []}
        valid_question = "a" * 2000

        response = client.post("/query", json={"question": valid_question})

        assert response.status_code == 200
