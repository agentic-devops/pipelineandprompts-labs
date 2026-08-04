from unittest.mock import Mock, patch

from app.ingest import embed_text, embed_texts, ingest_runbooks, load_and_chunk_runbooks


def _runbooks_path_mock(files):
    mock_path_instance = Mock()
    mock_path_instance.is_dir.return_value = True
    mock_path_instance.glob.return_value = files
    return mock_path_instance


class TestLoadAndChunkRunbooks:
    """Test runbook loading and chunking logic."""

    @patch("app.ingest.Path")
    @patch("app.ingest.settings")
    def test_loads_markdown_files(self, mock_settings, mock_path):
        mock_settings.runbooks_path = "./runbooks"
        mock_settings.chunk_size = 500
        mock_settings.chunk_overlap = 50

        mock_file = Mock()
        mock_file.stem = "test-runbook"
        mock_file.name = "test-runbook.md"
        mock_file.read_text.return_value = "# Test Runbook\n\nThis is test content."

        mock_path.return_value = _runbooks_path_mock([mock_file])

        chunks = load_and_chunk_runbooks()

        assert len(chunks) > 0
        assert chunks[0]["source"] == "test-runbook.md"
        assert "test-runbook-chunk-0" in chunks[0]["id"]

    @patch("app.ingest.Path")
    @patch("app.ingest.settings")
    def test_handles_empty_directory(self, mock_settings, mock_path):
        mock_settings.runbooks_path = "./empty"
        mock_path.return_value = _runbooks_path_mock([])

        assert load_and_chunk_runbooks() == []

    @patch("app.ingest.Path")
    @patch("app.ingest.settings")
    def test_skips_readme(self, mock_settings, mock_path):
        mock_settings.runbooks_path = "./runbooks"
        mock_settings.chunk_size = 500
        mock_settings.chunk_overlap = 50

        readme = Mock()
        readme.name = "README.md"
        readme.stem = "README"
        readme.read_text.return_value = "setup docs"

        mock_path.return_value = _runbooks_path_mock([readme])

        assert load_and_chunk_runbooks() == []

    @patch("app.ingest.Path")
    @patch("app.ingest.settings")
    def test_chunks_large_documents(self, mock_settings, mock_path):
        mock_settings.runbooks_path = "./runbooks"
        mock_settings.chunk_size = 100
        mock_settings.chunk_overlap = 20

        mock_file = Mock()
        mock_file.stem = "large-runbook"
        mock_file.name = "large-runbook.md"
        mock_file.read_text.return_value = "This is a test sentence. " * 50

        mock_path.return_value = _runbooks_path_mock([mock_file])

        chunks = load_and_chunk_runbooks()

        assert len(chunks) > 1
        assert all(c["source"] == "large-runbook.md" for c in chunks)


class TestEmbedText:
    """Test text embedding functionality."""

    @patch("app.ingest.client")
    def test_calls_openai_embedding_api(self, mock_client):
        mock_item = Mock(index=0, embedding=[0.1, 0.2, 0.3])
        mock_client.embeddings.create.return_value = Mock(data=[mock_item])

        result = embed_text("test text")

        mock_client.embeddings.create.assert_called_once_with(
            input=["test text"],
            model="text-embedding-3-small",
        )
        assert result == [0.1, 0.2, 0.3]

    @patch("app.ingest.client")
    def test_batches_multiple_texts(self, mock_client):
        mock_client.embeddings.create.return_value = Mock(
            data=[
                Mock(index=0, embedding=[0.1]),
                Mock(index=1, embedding=[0.2]),
            ]
        )

        result = embed_texts(["a", "b"])

        mock_client.embeddings.create.assert_called_once_with(
            input=["a", "b"],
            model="text-embedding-3-small",
        )
        assert result == [[0.1], [0.2]]


class TestIngestRunbooks:
    """Test full ingestion pipeline."""

    @patch("app.ingest.collection")
    @patch("app.ingest.embed_texts")
    @patch("app.ingest.load_and_chunk_runbooks")
    def test_ingests_chunks_to_chroma(self, mock_load, mock_embed, mock_collection):
        mock_load.return_value = [
            {"id": "test-chunk-0", "text": "content 1", "source": "test.md"},
            {"id": "test-chunk-1", "text": "content 2", "source": "test.md"},
        ]
        mock_embed.return_value = [[0.1] * 8, [0.2] * 8]

        result = ingest_runbooks()

        assert result["status"] == "ingested"
        assert result["chunks_ingested"] == 2
        assert result["runbooks_processed"] == 1
        mock_collection.upsert.assert_called_once()

    @patch("app.ingest.load_and_chunk_runbooks")
    def test_handles_no_runbooks(self, mock_load):
        mock_load.return_value = []

        result = ingest_runbooks()

        assert result["status"] == "no runbooks found"
        assert result["chunks_ingested"] == 0
        assert "hint" in result

    @patch("app.ingest.collection")
    @patch("app.ingest.embed_texts")
    @patch("app.ingest.load_and_chunk_runbooks")
    def test_uses_upsert_not_insert(self, mock_load, mock_embed, mock_collection):
        mock_load.return_value = [
            {"id": "test-chunk-0", "text": "content", "source": "test.md"}
        ]
        mock_embed.return_value = [[0.1] * 8]

        ingest_runbooks()

        mock_collection.upsert.assert_called_once()
        assert not mock_collection.add.called
