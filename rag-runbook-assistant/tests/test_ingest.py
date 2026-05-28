import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from app.ingest import load_and_chunk_runbooks, embed_text, ingest_runbooks


class TestLoadAndChunkRunbooks:
    """Test runbook loading and chunking logic."""

    @patch('app.ingest.Path')
    @patch('app.ingest.settings')
    def test_loads_markdown_files(self, mock_settings, mock_path):
        """Should load all .md files from runbooks directory."""
        mock_settings.runbooks_path = "./runbooks"
        mock_settings.chunk_size = 500
        mock_settings.chunk_overlap = 50

        # Mock file discovery
        mock_file = Mock()
        mock_file.stem = "test-runbook"
        mock_file.name = "test-runbook.md"
        mock_file.read_text.return_value = "# Test Runbook\n\nThis is test content."

        mock_path_instance = Mock()
        mock_path_instance.glob.return_value = [mock_file]
        mock_path.return_value = mock_path_instance

        chunks = load_and_chunk_runbooks()

        assert len(chunks) > 0
        assert chunks[0]["source"] == "test-runbook.md"
        assert "test-runbook-chunk-0" in chunks[0]["id"]

    @patch('app.ingest.Path')
    @patch('app.ingest.settings')
    def test_handles_empty_directory(self, mock_settings, mock_path):
        """Should return empty list when no runbooks found."""
        mock_settings.runbooks_path = "./empty"

        mock_path_instance = Mock()
        mock_path_instance.glob.return_value = []
        mock_path.return_value = mock_path_instance

        chunks = load_and_chunk_runbooks()

        assert chunks == []

    @patch('app.ingest.Path')
    @patch('app.ingest.settings')
    def test_chunks_large_documents(self, mock_settings, mock_path):
        """Should split large documents into multiple chunks."""
        mock_settings.runbooks_path = "./runbooks"
        mock_settings.chunk_size = 100  # Small chunk for testing
        mock_settings.chunk_overlap = 20

        # Create a large document
        large_content = "This is a test sentence. " * 50  # ~1250 chars

        mock_file = Mock()
        mock_file.stem = "large-runbook"
        mock_file.name = "large-runbook.md"
        mock_file.read_text.return_value = large_content

        mock_path_instance = Mock()
        mock_path_instance.glob.return_value = [mock_file]
        mock_path.return_value = mock_path_instance

        chunks = load_and_chunk_runbooks()

        # Should have multiple chunks
        assert len(chunks) > 1
        # All chunks should have same source
        assert all(c["source"] == "large-runbook.md" for c in chunks)


class TestEmbedText:
    """Test text embedding functionality."""

    @patch('app.ingest.client')
    def test_calls_openai_embedding_api(self, mock_client):
        """Should call OpenAI embeddings API with correct parameters."""
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1, 0.2, 0.3])]
        mock_client.embeddings.create.return_value = mock_response

        result = embed_text("test text")

        mock_client.embeddings.create.assert_called_once_with(
            input="test text",
            model="text-embedding-3-small"
        )
        assert result == [0.1, 0.2, 0.3]

    @patch('app.ingest.client')
    def test_returns_embedding_vector(self, mock_client):
        """Should return embedding vector as list of floats."""
        embedding = [0.1] * 1536  # Standard embedding size
        mock_response = Mock()
        mock_response.data = [Mock(embedding=embedding)]
        mock_client.embeddings.create.return_value = mock_response

        result = embed_text("test")

        assert isinstance(result, list)
        assert len(result) == 1536
        assert all(isinstance(x, float) for x in result)


class TestIngestRunbooks:
    """Test full ingestion pipeline."""

    @patch('app.ingest.collection')
    @patch('app.ingest.embed_text')
    @patch('app.ingest.load_and_chunk_runbooks')
    def test_ingests_chunks_to_chroma(self, mock_load, mock_embed, mock_collection):
        """Should embed and upsert all chunks to Chroma."""
        mock_load.return_value = [
            {"id": "test-chunk-0", "text": "content 1", "source": "test.md"},
            {"id": "test-chunk-1", "text": "content 2", "source": "test.md"}
        ]
        mock_embed.return_value = [0.1] * 1536

        result = ingest_runbooks()

        assert result["status"] == "ingested"
        assert result["chunks_ingested"] == 2
        assert result["runbooks_processed"] == 1
        assert mock_collection.upsert.call_count == 2

    @patch('app.ingest.load_and_chunk_runbooks')
    def test_handles_no_runbooks(self, mock_load):
        """Should return appropriate status when no runbooks found."""
        mock_load.return_value = []

        result = ingest_runbooks()

        assert result["status"] == "no runbooks found"
        assert result["chunks_ingested"] == 0

    @patch('app.ingest.collection')
    @patch('app.ingest.embed_text')
    @patch('app.ingest.load_and_chunk_runbooks')
    def test_uses_upsert_not_insert(self, mock_load, mock_embed, mock_collection):
        """Should use upsert to avoid duplicates on re-ingestion."""
        mock_load.return_value = [
            {"id": "test-chunk-0", "text": "content", "source": "test.md"}
        ]
        mock_embed.return_value = [0.1] * 1536

        ingest_runbooks()

        # Verify upsert was called, not add/insert
        mock_collection.upsert.assert_called_once()
        assert not mock_collection.add.called
