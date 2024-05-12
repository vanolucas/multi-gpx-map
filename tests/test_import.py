"""Test Multi GPX Map."""

import multi_gpx_map


def test_import() -> None:
    """Test that the app can be imported."""
    assert isinstance(multi_gpx_map.__name__, str)
