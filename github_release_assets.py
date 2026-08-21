from __future__ import annotations

from pathlib import Path
from urllib.request import Request, urlopen
import json


GITHUB_API = "https://api.github.com"


def _api_get(url: str) -> object:
    request = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "nifty-options-btst",
        },
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


def download_release_asset(
    owner: str,
    repo: str,
    tag: str,
    asset_name: str,
    destination: str | Path,
) -> Path:
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

    destination = Path(destination)

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    request = Request(
        str(url),
        headers={
            "Accept": (
                "application/octet-stream"
            ),
            "User-Agent": (
                "nifty-options-btst"
            ),
        },
    )

    with urlopen(request) as response:
        destination.write_bytes(
            response.read()
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