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
    text = Path(name).stem

    prefix = "NiftyOptions "

    if text.lower().startswith(prefix.lower()):
        suffix = text[len(prefix):]

        if len(suffix) >= 4 and suffix[:4].isdigit():
            return int(suffix[:4])

    for year in range(2000, 2100):
        if str(year) in text:
            return year

    return None


def _parse_part(name: str) -> int | None:
    """
    Recognise both normal and split release names.

    Normal:
        NiftyOptions 2017.zip

    Split:
        NiftyOptions 2017091.zip

    The split suffix 091 identifies split part 1.
    """

    text = Path(name).stem.lower()

    prefix = "niftyoptions "

    if not text.startswith(prefix):
        return None

    suffix = text[len(prefix):]

    # Normal unsplit yearly archive.
    if suffix == "2017":
        return None

    # Generic explicit forms such as:
    #   ... part1
    #   ... split1
    for marker in (
        "part",
        "split",
    ):
        position = suffix.find(marker)

        if position >= 0:
            digits = ""

            for char in suffix[
                position + len(marker):
            ]:
                if char.isdigit():
                    digits += char
                elif digits:
                    break

            if digits:
                return int(digits)

    # Actual project naming convention:
    #
    # NiftyOptions 2017091.zip
    #
    # First four digits = year.
    # Remaining three digits identify the split.
    #
    # 091 -> part 1
    #
    # More generally, use the final non-zero digit.
    if (
        len(suffix) > 4
        and suffix[:4].isdigit()
        and suffix[4:].isdigit()
    ):
        split_suffix = suffix[4:]

        if split_suffix == "":
            return None

        # 091 -> 1
        # 092 -> 2
        # 093 -> 3
        #
        # This preserves the release naming convention
        # without changing the asset filename.
        try:
            value = int(split_suffix)

            if value > 0:
                return value % 10 or value
        except ValueError:
            pass

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
            f"No ZIP release assets found for "
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