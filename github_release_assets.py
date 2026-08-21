from __future__ import annotations

from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen
import json
import os


GITHUB_API = "https://api.github.com"


def _api_get(url: str) -> object:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "nifty-options-btst",
        "X-GitHub-Api-Version": "2026-03-10",
    }

    token = os.environ.get("GH_TOKEN") or os.environ.get(
        "GITHUB_TOKEN"
    )

    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(
        url,
        headers=headers,
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
        f"{owner}/{repo}/releases/tags/{tag}"
    )

    result = _api_get(url)

    if not isinstance(result, dict):
        raise ValueError(
            "GitHub release response is not an object"
        )

    return result


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

    assets = release.get("assets", [])

    if not isinstance(assets, list):
        raise ValueError(
            "GitHub release assets are not a list"
        )

    return [
        asset
        for asset in assets
        if isinstance(asset, dict)
    ]


def _normalise_asset_name(
    name: str,
) -> str:
    return (
        name.strip()
        .replace("\\", "/")
        .rsplit("/", 1)[-1]
        .casefold()
    )


def find_release_asset(
    owner: str,
    repo: str,
    tag: str,
    asset_name: str,
) -> dict:
    assets = list_release_assets(
        owner,
        repo,
        tag,
    )

    target = _normalise_asset_name(
        asset_name
    )

    for asset in assets:
        name = str(
            asset.get("name", "")
        )

        if _normalise_asset_name(name) == target:
            return asset

    available = [
        str(
            asset.get("name", "")
        )
        for asset in assets
    ]

    raise FileNotFoundError(
        "Release asset not found: "
        f"{asset_name}. "
        "Available assets: "
        f"{available}"
    )


def _direct_release_asset_url(
    owner: str,
    repo: str,
    tag: str,
    asset_name: str,
) -> str:
    encoded_name = quote(
        asset_name,
        safe="",
    )

    return (
        f"https://github.com/"
        f"{owner}/{repo}/releases/download/"
        f"{quote(tag, safe='')}/"
        f"{encoded_name}"
    )


def _download_url(
    url: str,
) -> bytes:
    headers = {
        "Accept": "application/octet-stream",
        "User-Agent": "nifty-options-btst",
    }

    token = os.environ.get("GH_TOKEN") or os.environ.get(
        "GITHUB_TOKEN"
    )

    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(
        url,
        headers=headers,
    )

    with urlopen(request) as response:
        return response.read()


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

    try:
        asset = find_release_asset(
            owner,
            repo,
            tag,
            asset_name,
        )

        url = asset.get(
            "browser_download_url"
        )

        if not url:
            raise ValueError(
                "Release asset has no "
                "browser download URL"
            )

    except FileNotFoundError:
        # GitHub's public release page can expose the assets
        # even when the release-by-tag API response available
        # to the runner reports an empty assets array.
        #
        # GitHub's documented browser download URL is stable:
        # /releases/download/<tag>/<asset-name>
        url = _direct_release_asset_url(
            owner,
            repo,
            tag,
            asset_name,
        )

    data = _download_url(url)

    if not data:
        raise ValueError(
            f"Downloaded release asset is empty: "
            f"{asset_name}"
        )

    destination.write_bytes(data)

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

    downloaded: list[Path] = []

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