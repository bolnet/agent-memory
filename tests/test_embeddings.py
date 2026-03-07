"""Tests for the embedding module (mocked — no real API calls)."""

from unittest.mock import MagicMock, patch

import pytest

import agent_memory.embeddings as emb


@pytest.fixture(autouse=True)
def reset_embedding_state():
    """Reset module globals between tests."""
    emb.reset()
    yield
    emb.reset()


class TestAvailability:
    def test_not_available_without_keys(self):
        with patch.dict("os.environ", {}, clear=True):
            assert emb.available() is False

    def test_not_available_without_openai_package(self):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}):
            emb.reset()
            with patch.dict("sys.modules", {"openai": None}):
                emb.reset()
                # The import will fail, so available should be False
                assert emb.available() is False


class TestGetEmbedding:
    def test_returns_none_when_unavailable(self):
        with patch.dict("os.environ", {}, clear=True):
            result = emb.get_embedding("test text")
            assert result is None

    def test_returns_embedding_with_mocked_client(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_data = MagicMock()
        mock_data.embedding = [0.1] * 1536
        mock_response.data = [mock_data]
        mock_client.embeddings.create.return_value = mock_response

        emb._client = mock_client
        emb._initialized = True
        emb._model = "text-embedding-3-small"

        result = emb.get_embedding("test text")
        assert result is not None
        assert len(result) == 1536
        mock_client.embeddings.create.assert_called_once()

    def test_returns_none_on_api_error(self):
        mock_client = MagicMock()
        mock_client.embeddings.create.side_effect = Exception("API error")

        emb._client = mock_client
        emb._initialized = True

        result = emb.get_embedding("test text")
        assert result is None


class TestGetEmbeddingsBatch:
    def test_returns_nones_when_unavailable(self):
        with patch.dict("os.environ", {}, clear=True):
            results = emb.get_embeddings_batch(["a", "b", "c"])
            assert results == [None, None, None]

    def test_returns_embeddings_with_mocked_client(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_data_1 = MagicMock()
        mock_data_1.embedding = [0.1] * 1536
        mock_data_2 = MagicMock()
        mock_data_2.embedding = [0.2] * 1536
        mock_response.data = [mock_data_1, mock_data_2]
        mock_client.embeddings.create.return_value = mock_response

        emb._client = mock_client
        emb._initialized = True
        emb._model = "text-embedding-3-small"

        results = emb.get_embeddings_batch(["text1", "text2"])
        assert len(results) == 2
        assert all(len(r) == 1536 for r in results)


class TestReset:
    def test_reset_clears_state(self):
        emb._initialized = True
        emb._client = "something"
        emb.reset()
        assert emb._initialized is False
        assert emb._client is None
