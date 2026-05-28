import pytest
from unittest.mock import Mock, patch
from app.query import query_runbooks, SYSTEM_PROMPT


class TestQueryRunbooks:
    """Test query pipeline functionality."""

    @patch('app.query.client')
    @patch('app.query.collection')
    @patch('app.query.embed_text')
    def test_retrieves_relevant_chunks(self, mock_embed, mock_collection, mock_client):
        """Should embed question and retrieve similar chunks from Chroma."""
        mock_embed.return_value = [0.1] * 1536
        mock_collection.query.return_value = {
            "documents": [["chunk 1 content", "chunk 2 content"]],
            "metadatas": [[{"source": "test.md"}, {"source": "test.md"}]],
            "distances": [[0.1, 0.2]]
        }

        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Test answer"))]
        mock_client.chat.completions.create.return_value = mock_response

        result = query_runbooks("test question")

        # Should embed the question
        mock_embed.assert_called_once_with("test question")

        # Should query collection
        mock_collection.query.assert_called_once()
        call_args = mock_collection.query.call_args
        assert call_args.kwargs["query_embeddings"] == [[0.1] * 1536]

    @patch('app.query.client')
    @patch('app.query.collection')
    @patch('app.query.embed_text')
    def test_passes_context_to_llm(self, mock_embed, mock_collection, mock_client):
        """Should format retrieved chunks as context and pass to LLM."""
        mock_embed.return_value = [0.1] * 1536
        mock_collection.query.return_value = {
            "documents": [["Solution: restart the service"]],
            "metadatas": [[{"source": "troubleshooting.md"}]],
            "distances": [[0.1]]
        }

        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Answer based on context"))]
        mock_client.chat.completions.create.return_value = mock_response

        result = query_runbooks("how to fix the service?")

        # Should call LLM with system prompt and context
        call_args = mock_client.chat.completions.create.call_args
        messages = call_args.kwargs["messages"]

        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == SYSTEM_PROMPT
        assert messages[1]["role"] == "user"
        assert "troubleshooting.md" in messages[1]["content"]
        assert "Solution: restart the service" in messages[1]["content"]

    @patch('app.query.client')
    @patch('app.query.collection')
    @patch('app.query.embed_text')
    def test_returns_answer_with_sources(self, mock_embed, mock_collection, mock_client):
        """Should return LLM answer and source citations."""
        mock_embed.return_value = [0.1] * 1536
        mock_collection.query.return_value = {
            "documents": [["content 1", "content 2"]],
            "metadatas": [[{"source": "doc1.md"}, {"source": "doc2.md"}]],
            "distances": [[0.1, 0.2]]
        }

        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="The answer is 42"))]
        mock_client.chat.completions.create.return_value = mock_response

        result = query_runbooks("what is the answer?")

        assert result["answer"] == "The answer is 42"
        assert "doc1.md" in result["sources"]
        assert "doc2.md" in result["sources"]

    @patch('app.query.collection')
    @patch('app.query.embed_text')
    def test_handles_no_results(self, mock_embed, mock_collection):
        """Should return appropriate message when no relevant chunks found."""
        mock_embed.return_value = [0.1] * 1536
        mock_collection.query.return_value = {
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]]
        }

        result = query_runbooks("obscure question")

        assert result["answer"] == "No relevant runbooks found for this query."
        assert result["sources"] == []

    @patch('app.query.client')
    @patch('app.query.collection')
    @patch('app.query.embed_text')
    def test_uses_low_temperature(self, mock_embed, mock_collection, mock_client):
        """Should use low temperature for factual answers."""
        mock_embed.return_value = [0.1] * 1536
        mock_collection.query.return_value = {
            "documents": [["content"]],
            "metadatas": [[{"source": "test.md"}]],
            "distances": [[0.1]]
        }

        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Answer"))]
        mock_client.chat.completions.create.return_value = mock_response

        query_runbooks("test")

        call_args = mock_client.chat.completions.create.call_args
        assert call_args.kwargs["temperature"] == 0.2

    @patch('app.query.client')
    @patch('app.query.collection')
    @patch('app.query.embed_text')
    def test_deduplicates_sources(self, mock_embed, mock_collection, mock_client):
        """Should deduplicate source citations when multiple chunks from same file."""
        mock_embed.return_value = [0.1] * 1536
        mock_collection.query.return_value = {
            "documents": [["chunk 1", "chunk 2", "chunk 3"]],
            "metadatas": [
                [{"source": "doc.md"}, {"source": "doc.md"}, {"source": "other.md"}]
            ],
            "distances": [[0.1, 0.2, 0.3]]
        }

        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Answer"))]
        mock_client.chat.completions.create.return_value = mock_response

        result = query_runbooks("test")

        # Should only list each source once
        assert len(result["sources"]) == 2
        assert "doc.md" in result["sources"]
        assert "other.md" in result["sources"]
