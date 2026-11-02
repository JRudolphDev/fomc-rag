from fomc_rag.fetch import fetch_cached

URL = "https://example.com/page.htm"


def test_fetch_cached_returns_cached_file(tmp_path, no_network):
    # Arrange: put a file in the cache under the name fetch_cached will look for
    (tmp_path / "page.htm").write_bytes(b"<html>cached</html>")

    # Act
    result = fetch_cached(URL, tmp_path)

    # Assert
    assert result == "<html>cached</html>"


def test_fetch_cached_strips_bom(tmp_path, no_network):
    # Arrange: the first three bytes are a UTF-8 BOM
    (tmp_path / "page.htm").write_bytes(b"\xef\xbb\xbf<html>bom</html>")

    # Act
    result = fetch_cached(URL, tmp_path)

    # Assert
    assert result == "<html>bom</html>"
