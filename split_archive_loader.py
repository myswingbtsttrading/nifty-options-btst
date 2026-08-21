from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Iterable
import zipfile


def _normalise(name: str) -> str:
    return Path(name).name.lower()


def _read_zip_members(
    archive_path: str | Path,
) -> list[tuple[str, bytes]]:
    archive_path = Path(archive_path)

    if not archive_path.exists():
        raise FileNotFoundError(
            f"Archive not found: {archive_path}"
        )

    result: list[tuple[str, bytes]] = []

    with zipfile.ZipFile(
        archive_path,
        "r",
    ) as archive:
        for member in archive.infolist():
            if member.is_dir():
                continue

            result.append(
                (
                    member.filename,
                    archive.read(member.filename),
                )
            )

    return result


def _zip_bytes(
    members: Iterable[tuple[str, bytes]],
) -> bytes:
    buffer = BytesIO()

    with zipfile.ZipFile(
        buffer,
        "w",
        zipfile.ZIP_DEFLATED,
    ) as archive:
        for name, data in members:
            archive.writestr(
                name,
                data,
            )

    return buffer.getvalue()


def merge_zip_archives(
    archive_paths: Iterable[str | Path],
) -> bytes:
    """
    Merge the contents of multiple ZIP archives into
    one logical ZIP.

    Later archives replace an identically named member.
    """

    merged: dict[str, tuple[str, bytes]] = {}

    for archive_path in archive_paths:
        for name, data in _read_zip_members(
            archive_path
        ):
            merged[_normalise(name)] = (
                name,
                data,
            )

    return _zip_bytes(
        merged.values()
    )


def merge_year_release_assets(
    archive_paths: Iterable[str | Path],
) -> bytes:
    """
    Merge split yearly release assets into one logical
    ZIP archive.
    """

    paths = [
        Path(path)
        for path in archive_paths
    ]

    if not paths:
        raise ValueError(
            "At least one archive is required"
        )

    return merge_zip_archives(
        paths
    )


def merged_member_names(
    archive_paths: Iterable[str | Path],
) -> list[str]:
    """
    Return the unique member names represented by
    all supplied archives.
    """

    names: dict[str, str] = {}

    for archive_path in archive_paths:
        for name, _ in _read_zip_members(
            archive_path
        ):
            names[_normalise(name)] = name

    return sorted(
        names.values(),
        key=str.lower,
    )