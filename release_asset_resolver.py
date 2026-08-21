from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class ReleaseAsset:
    path: Path
    name: str
    year: int
    part: int | None


def _normalise(name: str) -> str:
    return name.strip().lower()


def _parse_year(name: str) -> int | None:
    text = _normalise(name)

    for year in range(2000, 2100):
        if str(year) in text:
            return year

    return None


def _parse_part(name: str) -> int | None:
    text = _normalise(name)

    markers = (
        "part",
        "split",
    )

    for marker in markers:
        position = text.find(marker)

        if position < 0:
            continue

        suffix = text[
            position + len(marker):
        ]

        digits = ""

        for char in suffix:
            if char.isdigit():
                digits += char
            elif digits:
                break

        if digits:
            return int(digits)

    return None


def _is_zip(path: Path) -> bool:
    return (
        path.is_file()
        and path.suffix.lower() == ".zip"
    )


def discover_release_assets(
    release_dir: str | Path,
) -> list[ReleaseAsset]:
    release_dir = Path(release_dir)

    if not release_dir.exists():
        raise FileNotFoundError(
            f"Release directory not found: "
            f"{release_dir}"
        )

    assets: list[ReleaseAsset] = []

    for path in sorted(release_dir.iterdir()):
        if not _is_zip(path):
            continue

        year = _parse_year(path.name)

        if year is None:
            continue

        assets.append(
            ReleaseAsset(
                path=path,
                name=path.name,
                year=year,
                part=_parse_part(path.name),
            )
        )

    return assets


def find_year_assets(
    release_dir: str | Path,
    year: int,
) -> list[ReleaseAsset]:
    assets = discover_release_assets(
        release_dir
    )

    return [
        asset
        for asset in assets
        if asset.year == year
    ]


def find_primary_year_asset(
    release_dir: str | Path,
    year: int,
) -> ReleaseAsset:
    assets = find_year_assets(
        release_dir,
        year,
    )

    if not assets:
        raise FileNotFoundError(
            f"No ZIP release asset found for "
            f"{year}"
        )

    unsplit = [
        asset
        for asset in assets
        if asset.part is None
    ]

    if unsplit:
        return unsplit[0]

    return assets[0]


def find_split_year_assets(
    release_dir: str | Path,
    year: int,
) -> list[ReleaseAsset]:
    assets = find_year_assets(
        release_dir,
        year,
    )

    return [
        asset
        for asset in assets
        if asset.part is not None
    ]


def resolve_year_archives(
    release_dir: str | Path,
    year: int,
) -> dict[str, object]:
    assets = find_year_assets(
        release_dir,
        year,
    )

    if not assets:
        raise FileNotFoundError(
            f"No release ZIP assets found for "
            f"{year}"
        )

    primary = [
        asset
        for asset in assets
        if asset.part is None
    ]

    split = [
        asset
        for asset in assets
        if asset.part is not None
    ]

    split.sort(
        key=lambda asset: (
            asset.part
            if asset.part is not None
            else 0
        )
    )

    return {
        "year": year,
        "assets": assets,
        "primary": primary,
        "split": split,
        "asset_count": len(assets),
        "split_count": len(split),
        "has_primary": bool(primary),
        "has_split": bool(split),
    }


def validate_year_release_assets(
    release_dir: str | Path,
    year: int,
    expected_names: Iterable[str] | None = None,
) -> dict[str, object]:
    assets = find_year_assets(
        release_dir,
        year,
    )

    names = {
        _normalise(asset.name)
        for asset in assets
    }

    expected = list(
        expected_names or []
    )

    missing = [
        name
        for name in expected
        if _normalise(name) not in names
    ]

    return {
        "year": year,
        "asset_count": len(assets),
        "assets": [
            asset.name
            for asset in assets
        ],
        "missing": missing,
        "valid": not missing,
    }