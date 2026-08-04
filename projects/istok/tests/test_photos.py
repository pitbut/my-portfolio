import io
from unittest.mock import MagicMock, patch

from app.photos import upload_photo


def _fake_file(filename="photo.jpg", content=b"fake-image-bytes", mimetype="image/jpeg"):
    from werkzeug.datastructures import FileStorage

    return FileStorage(stream=io.BytesIO(content), filename=filename, content_type=mimetype)


def test_upload_photo_returns_none_without_file(app):
    with app.app_context():
        url, error = upload_photo(None)
    assert url is None
    assert error is None


def test_upload_photo_returns_error_without_api_key(app):
    with app.app_context():
        assert app.config.get("IMGBB_API_KEY") is None
        url, error = upload_photo(_fake_file())
    assert url is None
    assert error is not None


def test_upload_photo_rejects_non_image(app):
    app.config["IMGBB_API_KEY"] = "test-key"
    with app.app_context():
        url, error = upload_photo(_fake_file(mimetype="text/plain"))
    assert url is None
    assert "изображением" in error


def test_upload_photo_success(app):
    app.config["IMGBB_API_KEY"] = "test-key"
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.json.return_value = {"success": True, "data": {"url": "https://i.ibb.co/abc/photo.jpg"}}

    with app.app_context():
        with patch("app.photos.requests.post", return_value=mock_response) as mock_post:
            url, error = upload_photo(_fake_file())

    assert url == "https://i.ibb.co/abc/photo.jpg"
    assert error is None
    assert mock_post.call_args.kwargs["params"] == {"key": "test-key"}


def test_upload_photo_handles_api_failure(app):
    app.config["IMGBB_API_KEY"] = "test-key"
    mock_response = MagicMock()
    mock_response.ok = False
    mock_response.json.return_value = {"success": False}

    with app.app_context():
        with patch("app.photos.requests.post", return_value=mock_response):
            url, error = upload_photo(_fake_file())

    assert url is None
    assert error is not None


def test_upload_photo_handles_network_error(app):
    import requests

    app.config["IMGBB_API_KEY"] = "test-key"
    with app.app_context():
        with patch("app.photos.requests.post", side_effect=requests.ConnectionError("boom")):
            url, error = upload_photo(_fake_file())

    assert url is None
    assert error is not None
