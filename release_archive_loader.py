from __future__ import annotations

from pathlib import Path
from typing import Iterable, List
import zipfile


def _normalise(name: str) -> str:
    return Path(name).name.lower()


def find_release_asset(
    release_dir: str | Path,
    asset_name: str,
) -> Path:
    """
    Find an exact release asset in a local release-assets directory.
    Matching is case-insensitive and ignores surrounding paths.
    """

    release_dir = Path(release_dir)

    if not release_dir.exists():
        raise FileNotFoundError(
            f"Release directory not found: {release_dir}"
        )

    target = _normalise(asset_name)

    for path in release_dir.iterdir():
        if path.is_file() and _normalise(path.name) == target:
            return path

    raise FileNotFoundError(
        f"Release asset not found: {asset_name}"
    )


def list_zip_members(
    archive_path: str | Path,
) -> List[str]:
    """
    Return all members from a ZIP archive.
    """

    archive_path = Path(archive_path)

    if not archive_path.exists():
        raise FileNotFoundError(
            f"Archive not found: {archive_path}"
        )

    with zipfile.ZipFile(
        archive_path,
        "r",
    ) as archive:
        return archive.namelist()


def find_monthly_zip(
    archive_path: str | Path,
    monthly_zip_name: str,
) -> str:
    """
    Find a monthly ZIP inside a yearly release archive.
    """

    target = _normalise(monthly_zip_name)

    with zipfile.ZipFile(
        archive_path,
        "r",
    ) as archive:
        for member in archive.namelist():
            if _normalise(member) == target:
                return member

    raise FileNotFoundError(
        f"Monthly ZIP not found: {monthly_zip_name}"
    )


def read_monthly_zip(
    archive_path: str | Path,
    monthly_zip_name: str,
) -> bytes:
    """
    Read the complete monthly ZIP from a yearly archive.
    """

    with zipfile.ZipFile(
        archive_path,
        "r",
    ) as archive:

        member = find_monthly_zip(
            archive_path,
            monthly_zip_name,
        )

        return archive.read(member)


def validate_release_archive(
    archive_path: str | Path,
    expected_months: Iterable[str],
) -> dict:
    """
    Validate that a yearly release archive contains
    the requested monthly ZIP assets.
    """

    archive_path = Path(archive_path)

    members = list_zip_members(
        archive_path
    )

    normalised_members = {
        _normalise(member)
        for member in members
    }

    found = []
    missing = []

    for month_name in expected_months:
        if _normalise(month_name) in normalised_members:
            found.append(month_name)
        else:
            missing.append(month_name)

    return {
        "archive": archive_path.name,
        "member_count": len(members),
        "found_months": found,
        "missing_months": missing,
        "valid": not missing,
    }