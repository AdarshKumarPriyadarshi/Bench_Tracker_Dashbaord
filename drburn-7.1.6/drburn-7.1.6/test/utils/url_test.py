from pathlib import Path

from utils.url import is_url


class TestUrl:

    def test_is_url_with_path_string(self):
        # Given
        url = "path/to"
        # When
        actual = is_url(url)
        # Then
        assert actual is False

    def test_is_url_with_pathlib(self):
        # Given
        url = Path("path/to")
        # When
        actual = is_url(url)
        # Then
        assert actual is False

    def test_is_url_with_https_string(self):
        # Given
        url = "https://host.com/path/to"
        # When
        actual = is_url(url)
        # Then
        assert actual is True
