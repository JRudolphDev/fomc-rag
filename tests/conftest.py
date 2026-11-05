import pytest


@pytest.fixture
def no_network(monkeypatch):
    """Fail the test if fetch_cached tries to download."""

    def fail(*args, **kwargs):
        pytest.fail("network called on what should be a cache hit")

    monkeypatch.setattr("fomc_rag.fetch.requests.get", fail)
