from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen


GITHUB_API = "https://api.github.com"


def _token() -> str | None:
    return (
        os.environ.get("GH_TOKEN")
        or os.environ.get("GITHUB_TOKEN")
    )


def _headers(
    accept: str = "application/vnd.github+json",
) -> dict[str, str]:
    headers = {
        "Accept": accept,
        "User-Agent": "nifty-options-btst",
    }

    token = _token()

    if token:
        headers["Authorization"] = f"Bearer {token}"

    return headers


def _api_get(url: str) -> object:
    request = Request(
        url,
        headers=_headers(),
    )

    with urlopen(request) as response:
        return json.loads(
            response.read().decode("utf-8")
        )


def get_release(
    owner: str,
    repo: str,
    tag: str,
) -> dict:
    url = (
        f"{GITHUB_API}/repos/"
        f"{quote(owner, safe='')}/"
        f"{quote(repo, safe='')}/"
        f"releases/tags/"
        f"{quote(tag, safe='')}"
    )

    result = _api_get(url)

    if not isinstance(result, dict):
        raise ValueError(
            "GitHub release response is not an object"
        )

    return result


def _normalise_asset_name(
    name: str,
) -> str:
    """
    Normalise release asset names so that:

        November 2017.zip
        November.2017.zip

    are treated as the same asset.

    GitHub release assets may be uploaded with spaces converted
    to periods, while the application may request the original
    filename containing spaces.
    """
    value = (
        str(name)
        .strip()
        .replace("\\", "/")
        .rsplit("/", 1)[-1]
        .casefold()
    )

    # GitHub-uploaded filenames may use periods instead of spaces.
    value = value.replace(".", " ")

    # Collapse repeated whitespace.
    return " ".join(value.split())


def _asset_from_release(
    release: dict,
    asset_name: str,
) -> dict | None:
    assets = release.get("assets")

    if not isinstance(assets, list):
        return None

    target = _normalise_asset_name(
        asset_name
    )

    for asset in assets:
        if not isinstance(asset, dict):
            continue

        if (
            _normalise_asset_name(
                asset.get("name", "")
            )
            == target
        ):
            return asset

    return None


def list_release_assets(
    owner: str,
    repo: str,
    tag: str,
) -> list[dict]:
    release = get_release(
        owner,
        repo,
        tag,
    )

    assets = release.get("assets")

    if isinstance(assets, list):
        return [
            asset
            for asset in assets
            if isinstance(asset, dict)
        ]

    return []


def find_release_asset(
    owner: str,
    repo: str,
    tag: str,
    asset_name: str,
) -> dict:
    release = get_release(
        owner,
        repo,
        tag,
    )

    asset = _asset_from_release(
        release,
        asset_name,
    )

    if asset is not None:
        return asset

    assets = release.get("assets")

    available = []

    if isinstance(assets, list):
        available = [
            str(
                asset.get(
                    "name",
                    "",
                )
            )
            for asset in assets
            if isinstance(asset, dict)
        ]

    raise FileNotFoundError(
        "Release asset not found: "
        f"{asset_name}. "
        f"Available assets: {available}"
    )


def _download_url(
    url: str,
) -> bytes:
    request = Request(
        url,
        headers=_headers(
            "application/octet-stream"
        ),
    )

    with urlopen(request) as response:
        return response.read()


def _direct_release_asset_url(
    owner: str,
    repo: str,
    tag: str,
    asset_name: str,
) -> str:
    return (
        "https://github.com/"
        f"{quote(owner, safe='')}/"
        f"{quote(repo, safe='')}/"
        "releases/download/"
        f"{quote(tag, safe='')}/"
        f"{quote(asset_name, safe='')}"
    )


def _asset_name_candidates(
    asset_name: str,
) -> list[str]:
    """
    Return possible release-download filenames.

    The primary filename is kept unchanged. A second candidate
    replaces spaces with periods because GitHub-uploaded release
    assets in this repository currently use names such as:

        November.2017.zip
    """
    candidates = [asset_name]

    dotted = asset_name.replace(
        " ",
        ".",
    )

    if dotted != asset_name:
        candidates.append(dotted)

    return candidates


def _download_direct_release_asset(
    owner: str,
    repo: str,
    tag: str,
    asset_name: str,
) -> bytes:
    last_error: Exception | None = None

    for candidate in _asset_name_candidates(
        asset_name
    ):
        url = _direct_release_asset_url(
            owner,
            repo,
            tag,
            candidate,
        )

        try:
            data = _download_url(url)

            if data:
                return data

        except Exception as exc:
            last_error = exc

    if last_error is not None:
        raise last_error

    raise ValueError(
        "Downloaded release asset is empty: "
        f"{asset_name}"
    )


def download_release_asset(
    owner: str,
    repo: str,
    tag: str,
    asset_name: str,
    destination: str | Path,
) -> Path:
    destination = Path(destination)

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # First obtain the release metadata.
    release = get_release(
        owner,
        repo,
        tag,
    )

    asset = _asset_from_release(
        release,
        asset_name,
    )

    if asset is not None:
        browser_url = asset.get(
            "browser_download_url"
        )

        if browser_url:
            data = _download_url(
                browser_url
            )
        else:
            asset_id = asset.get("id")

            if not asset_id:
                raise ValueError(
                    "Release asset has neither "
                    "browser_download_url nor id: "
                    f"{asset_name}"
                )

            api_url = (
                f"{GITHUB_API}/repos/"
                f"{quote(owner, safe='')}/"
                f"{quote(repo, safe='')}/"
                "releases/assets/"
                f"{asset_id}"
            )

            data = _download_url(
                api_url
            )

    else:
        # GitHub's stable release-download URL.
        #
        # Try the requested filename first and then the
        # dotted filename used by the current release.
        data = _download_direct_release_asset(
            owner=owner,
            repo=repo,
            tag=tag,
            asset_name=asset_name,
        )

    if not data:
        raise ValueError(
            "Downloaded release asset is empty: "
            f"{asset_name}"
        )

    destination.write_bytes(
        data
    )

    return destination


def download_release_assets(
    owner: str,
    repo: str,
    tag: str,
    asset_names: list[str],
    destination_dir: str | Path,
) -> list[Path]:
    destination_dir = Path(
        destination_dir
    )

    destination_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    downloaded = []

    for asset_name in asset_names:
        destination = (
            destination_dir
            / Path(asset_name).name
        )

        downloaded.append(
            download_release_asset(
                owner=owner,
                repo=repo,
                tag=tag,
                asset_name=asset_name,
                destination=destination,
            )
        )

    return downloaded