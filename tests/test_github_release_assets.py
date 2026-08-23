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


def test_find_release_asset_is_case_insensitive(
    monkeypatch,
):
    expected = {
        "tag_name": "data-2017-v1",
        "assets": [
            {
                "name":
                    "NiftyOptions 2017.zip",
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


def test_find_release_asset_strips_path(
    monkeypatch,
):
    expected = {
        "tag_name": "data-2017-v1",
        "assets": [
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

    asset = (
        github_release_assets.find_release_asset(
            "myswingbtsttrading",
            "nifty-options-btst",
            "data-2017-v1",
            "/downloads/NiftyOptions 2017091.zip",
        )
    )

    assert (
        asset["name"]
        == "NiftyOptions 2017091.zip"
    )


def test_find_release_asset_matches_dots_and_spaces(
    monkeypatch,
):
    expected = {
        "tag_name": "data-2017-v1",
        "assets": [
            {
                "name":
                    "November.2017.zip",
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
            "November 2017.zip",
        )
    )

    assert (
        asset["name"]
        == "November.2017.zip"
    )


def test_find_release_asset_matches_all_months(
    monkeypatch,
):
    months = [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]

    expected = {
        "tag_name": "data-2017-v1",
        "assets": [
            {
                "name":
                    f"{month}.2017.zip",
            }
            for month in months
        ],
    }

    monkeypatch.setattr(
        github_release_assets,
        "_api_get",
        lambda url: expected,
    )

    for month in months:
        asset = (
            github_release_assets.find_release_asset(
                "myswingbtsttrading",
                "nifty-options-btst",
                "data-2017-v1",
                f"{month} 2017.zip",
            )
        )

        assert (
            asset["name"]
            == f"{month}.2017.zip"
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


def test_direct_release_asset_url():
    url = (
        github_release_assets
        ._direct_release_asset_url(
            "myswingbtsttrading",
            "nifty-options-btst",
            "data-2017-v1",
            "NiftyOptions 2017.zip",
        )
    )

    assert url == (
        "https://github.com/"
        "myswingbtsttrading/"
        "nifty-options-btst/"
        "releases/download/"
        "data-2017-v1/"
        "NiftyOptions%202017.zip"
    )


def test_download_uses_api_asset(
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

    monkeypatch.setattr(
        github_release_assets,
        "_download_url",
        lambda url: b"release-data",
    )

    destination = (
        tmp_path
        / "NiftyOptions 2017.zip"
    )

    result = (
        github_release_assets.download_release_asset(
            "myswingbtsttrading",
            "nifty-options-btst",
            "data-2017-v1",
            "NiftyOptions 2017.zip",
            destination,
        )
    )

    assert result == destination

    assert (
        destination.read_bytes()
        == b"release-data"
    )


def test_download_dot_named_asset_using_space_name(
    monkeypatch,
    tmp_path,
):
    expected = {
        "tag_name": "data-2017-v1",
        "assets": [
            {
                "name":
                    "November.2017.zip",
                "browser_download_url":
                    "https://example.com/November.2017.zip",
            },
        ],
    }

    monkeypatch.setattr(
        github_release_assets,
        "_api_get",
        lambda url: expected,
    )

    captured = {}

    def fake_download(url):
        captured["url"] = url
        return b"release-data"

    monkeypatch.setattr(
        github_release_assets,
        "_download_url",
        fake_download,
    )

    destination = (
        tmp_path
        / "November 2017.zip"
    )

    result = (
        github_release_assets.download_release_asset(
            "myswingbtsttrading",
            "nifty-options-btst",
            "data-2017-v1",
            "November 2017.zip",
            destination,
        )
    )

    assert result == destination

    assert (
        destination.read_bytes()
        == b"release-data"
    )

    assert captured["url"] == (
        "https://example.com/"
        "November.2017.zip"
    )


def test_download_falls_back_to_direct_url(
    monkeypatch,
    tmp_path,
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

    captured = {}

    def fake_download(url):
        captured["url"] = url
        return b"release-data"

    monkeypatch.setattr(
        github_release_assets,
        "_download_url",
        fake_download,
    )

    destination = (
        tmp_path
        / "NiftyOptions 2017.zip"
    )

    result = (
        github_release_assets.download_release_asset(
            "myswingbtsttrading",
            "nifty-options-btst",
            "data-2017-v1",
            "NiftyOptions 2017.zip",
            destination,
        )
    )

    assert result == destination

    assert (
        destination.read_bytes()
        == b"release-data"
    )

    assert captured["url"] == (
        "https://github.com/"
        "myswingbtsttrading/"
        "nifty-options-btst/"
        "releases/download/"
        "data-2017-v1/"
        "NiftyOptions%202017.zip"
    )


def test_download_multiple_assets(
    monkeypatch,
    tmp_path,
):
    expected = {
        "tag_name": "data-2017-v1",
        "assets": [
            {
                "name":
                    "January.2017.zip",
                "browser_download_url":
                    "https://example.com/January.2017.zip",
            },
            {
                "name":
                    "November.2017.zip",
                "browser_download_url":
                    "https://example.com/November.2017.zip",
            },
        ],
    }

    monkeypatch.setattr(
        github_release_assets,
        "_api_get",
        lambda url: expected,
    )

    monkeypatch.setattr(
        github_release_assets,
        "_download_url",
        lambda url: b"release-data",
    )

    result = (
        github_release_assets.download_release_assets(
            owner="myswingbtsttrading",
            repo="nifty-options-btst",
            tag="data-2017-v1",
            asset_names=[
                "January 2017.zip",
                "November 2017.zip",
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
        "January 2017.zip",
        "November 2017.zip",
    }