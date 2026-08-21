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
        f"{owner}/{repo}/releases/tags/"
        f"{quote(tag, safe='')}"
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

    assets = release.get("assets")

    if isinstance(assets, list) and assets:
        return [
            asset
            for asset in assets
            if isinstance(asset, dict)
        ]

    release_id = release.get("id")

    if not release_id:
        return []

    url = (
        f"{GITHUB_API}/repos/"
        f"{owner}/{repo}/releases/"
        f"{release_id}/assets"
        f"?per_page=100"
    )

    result = _api_get(url)

    if not isinstance(result, list):
        return []

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

    release = get_release(
        owner,
        repo,
        tag,
    )

    release_assets = release.get(
        "assets"
    )

    asset = None

    if isinstance(
        release_assets,
        list,
    ):
        target = _normalise_asset_name(
            asset_name
        )

        for candidate in release_assets:
            if not isinstance(
                candidate,
                dict,
            ):
                continue

            if (
                _normalise_asset_name(
                    candidate.get(
                        "name",
                        "",
                    )
                )
                == target
            ):
                asset = candidate
                break

    # If the normal release response did not expose
    # the asset, try the dedicated asset endpoint.
    if asset is None:
        release_id = release.get(
            "id"
        )

        if release_id:
            url = (
                f"{GITHUB_API}/repos/"
                f"{owner}/{repo}/releases/"
                f"{release_id}/assets"
                f"?per_page=100"
            )

            result = _api_get(url)

            if isinstance(
                result,
                list,
            ):
                target = (
                    _normalise_asset_name(
                        asset_name
                    )
                )

                for candidate in result:
                    if not isinstance(
                        candidate,
                        dict,
                    ):
                        continue

                    if (
                        _normalise_asset_name(
                            candidate.get(
                                "name",
                                "",
                            )
                        )
                        == target
                    ):
                        asset = candidate
                        break

    # Real GitHub release asset.
    if asset is not None:
        asset_id = asset.get("id")

        if asset_id:
            url = (
                f"{GITHUB_API}/repos/"
                f"{owner}/{repo}/releases/assets/"
                f"{asset_id}"
            )

            data = _download_url(url)

        else:
            browser_url = asset.get(
                "browser_download_url"
            )

            if not browser_url:
                raise FileNotFoundError(
                    "Release asset has no download URL: "
                    f"{asset_name}"
                )

            data = _download_url(
                browser_url
            )

    else:
        # Compatibility/direct-download fallback.
        #
        # This is also useful for tests and for GitHub's
        # stable release-download URL.
        url = _direct_release_asset_url(
            owner,
            repo,
            tag,
            asset_name,
        )

        data = _download_url(url)

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