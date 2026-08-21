from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen


GITHUB_API = "https://api.github.com"


def _headers(
    accept: str = "application/vnd.github+json",
) -> dict[str, str]:
    headers = {
        "Accept": accept,
        "User-Agent": "nifty-options-btst",
        "X-GitHub-Api-Version": "2026-03-10",
    }

    token = (
        os.environ.get("GH_TOKEN")
        or os.environ.get("GITHUB_TOKEN")
    )

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
        f"{owner}/{repo}/releases/tags/{quote(tag, safe='')}"
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

    release_id = release.get("id")

    if not release_id:
        raise ValueError(
            "GitHub release response has no release id"
        )

    # Do NOT rely on release["assets"].
    #
    # The release page shows the assets, while the
    # /releases/tags/{tag} response seen by the runner
    # reported an empty asset list. Fetch the dedicated
    # release-assets endpoint instead.
    url = (
        f"{GITHUB_API}/repos/"
        f"{owner}/{repo}/releases/"
        f"{release_id}/assets"
        f"?per_page=100"
    )

    result = _api_get(url)

    if not isinstance(result, list):
        raise ValueError(
            "GitHub release-assets response is not a list"
        )

    return [
        asset
        for asset in result
        if isinstance(asset, dict)
    ]


def _normalise_asset_name(
    name: str,
) -> str:
    return (
        str(name)
        .strip()
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
        name = asset.get("name", "")

        if (
            _normalise_asset_name(name)
            == target
        ):
            return asset

    available = [
        str(asset.get("name", ""))
        for asset in assets
    ]

    raise FileNotFoundError(
        "Release asset not found: "
        f"{asset_name}. "
        "Available assets: "
        f"{available}"
    )


def _download_url(
    url: str,
    *,
    accept: str = "application/octet-stream",
) -> bytes:
    request = Request(
        url,
        headers=_headers(accept),
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
        f"https://github.com/"
        f"{quote(owner, safe='')}/"
        f"{quote(repo, safe='')}/"
        f"releases/download/"
        f"{quote(tag, safe='')}/"
        f"{quote(asset_name, safe='')}"
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

    asset = find_release_asset(
        owner,
        repo,
        tag,
        asset_name,
    )

    asset_id = asset.get("id")

    if not asset_id:
        raise ValueError(
            "Release asset has no asset id: "
            f"{asset_name}"
        )

    # Download through the GitHub API asset endpoint.
    #
    # This avoids the 404 encountered with the public
    # /releases/download/... fallback URL.
    api_url = (
        f"{GITHUB_API}/repos/"
        f"{owner}/{repo}/releases/assets/"
        f"{asset_id}"
    )

    data = _download_url(
        api_url,
        accept="application/octet-stream",
    )

    if not data:
        raise ValueError(
            "Downloaded release asset is empty: "
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