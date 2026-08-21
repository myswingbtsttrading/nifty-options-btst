import json

import pytest

import github_release_assets


def test_get_release(
    monkeypatch,
):
    expected = {
        "tag_name": "data-2017-v1",
        "assets": [],
    }

    monkeypatch.setattr(
        github_release_assets,
        "_api_get",
        lambda url: expected,
    )

    result = (
        github_release_assets.get_release(
            "myswingbtsttrading",
            "nifty-options-btst",
            "data-2017-v1",
        )
    )

    assert result == expected


def test_list_release_assets(
    monkeypatch,
):
    expected = {
        "tag_name": "data-2017-v1",
        "assets": [
            {
                "name":
                    "NiftyOptions 2017.zip",
            },
            {
                "name":
                    "NiftyOptions 2017091.zip",
            },
        ],
    }

    monkeypatch.setattr(
        github_release_assets,
        "_api_get",
        lambda url: expected,
    )

    assets = (
        github_release_assets.list_release_assets(
            "myswingbtsttrading",
            "nifty-options-btst",
            "data-2017-v1",
        )
    )

    assert len(assets) == 2

    assert (
        assets[0]["name"]
        == "NiftyOptions 2017.zip"
    )

    assert (
        assets[1]["name"]
        == "NiftyOptions 2017091.zip"
    )


def test_find_release_asset(
    monkeypatch,
):
    expected = {
        "tag_name": "data-2017-v1",
        "assets": [
            {
                "name":
                    "NiftyOptions 2017.zip",
                "browser_download_url":
                    "https://example.com/2017.zip",
            },
        ],
    }

    monkeypatch.setattr(
        github_release_assets,
        "_api_get",
        lambda url: expected,
    )

    asset = (
        github_release_assets.find_release_asset(
            "myswingbtsttrading",
            "nifty-options-btst",
            "data-2017-v1",
            "NIFTYOPTIONS 2017.ZIP",
        )
    )

    assert (
        asset["name"]
        == "NiftyOptions 2017.zip"
    )


def test_missing_release_asset_raises(
    monkeypatch,
):
    expected = {
        "tag_name": "data-2017-v1",
        "assets": [],
    }

    monkeypatch.setattr(
        github_release_assets,
        "_api_get",
        lambda url: expected,
    )

    with pytest.raises(
        FileNotFoundError,
        match="Release asset not found",
    ):
        github_release_assets.find_release_asset(
            "myswingbtsttrading",
            "nifty-options-btst",
            "data-2017-v1",
            "missing.zip",
        )


def test_download_release_asset(
    monkeypatch,
    tmp_path,
):
    expected = {
        "tag_name": "data-2017-v1",
        "assets": [
            {
                "name":
                    "NiftyOptions 2017.zip",
                "browser_download_url":
                    "https://example.com/2017.zip",
            },
        ],
    }

    monkeypatch.setattr(
        github_release_assets,
        "_api_get",
        lambda url: expected,
    )

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(
            self,
            exc_type,
            exc_value,
            traceback,
        ):
            return False

        def read(self):
            return b"release-data"

    monkeypatch.setattr(
        github_release_assets,
        "urlopen",
        lambda request: FakeResponse(),
    )

    destination = (
        tmp_path
        / "downloads"
        / "NiftyOptions 2017.zip"
    )

    result = (
        github_release_assets.download_release_asset(
            owner="myswingbtsttrading",
            repo="nifty-options-btst",
            tag="data-2017-v1",
            asset_name="NiftyOptions 2017.zip",
            destination=destination,
        )
    )

    assert result == destination
    assert destination.read_bytes() == b"release-data"


def test_download_multiple_assets(
    monkeypatch,
    tmp_path,
):
    expected = {
        "tag_name": "data-2017-v1",
        "assets": [
            {
                "name":
                    "NiftyOptions 2017.zip",
                "browser_download_url":
                    "https://example.com/2017.zip",
            },
            {
                "name":
                    "NiftyOptions 2017091.zip",
                "browser_download_url":
                    "https://example.com/2017091.zip",
            },
        ],
    }

    monkeypatch.setattr(
        github_release_assets,
        "_api_get",
        lambda url: expected,
    )

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(
            self,
            exc_type,
            exc_value,
            traceback,
        ):
            return False

        def read(self):
            return b"release-data"

    monkeypatch.setattr(
        github_release_assets,
        "urlopen",
        lambda request: FakeResponse(),
    )

    result = (
        github_release_assets.download_release_assets(
            owner="myswingbtsttrading",
            repo="nifty-options-btst",
            tag="data-2017-v1",
            asset_names=[
                "NiftyOptions 2017.zip",
                "NiftyOptions 2017091.zip",
            ],
            destination_dir=tmp_path,
        )
    )

    assert len(result) == 2

    assert all(
        path.exists()
        for path in result
    )

    assert {
        path.name
        for path in result
    } == {
        "NiftyOptions 2017.zip",
        "NiftyOptions 2017091.zip",
    }