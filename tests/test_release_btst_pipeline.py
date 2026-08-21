from datetime import date
import io
import zipfile

import release_btst_pipeline


def _make_month_zip() -> bytes:
    data = """PE 10050,2017/10/26,14:59,55,56,54,55.00,100
PE 10050,2017/10/26,15:00,55,56,54,55.55,100
PE 10050,2017/10/27,09:14,49,50,48,49.50,100
PE 10050,2017/10/27,09:15,49,50,48,49.65,150
"""

    buffer = io.BytesIO()

    with zipfile.ZipFile(
        buffer,
        "w",
        zipfile.ZIP_DEFLATED,
    ) as archive:
        archive.writestr(
            "PE 10050.txt",
            data,
        )

    return buffer.getvalue()


def _make_year_zip(
    month_name: str,
) -> bytes:
    buffer = io.BytesIO()

    with zipfile.ZipFile(
        buffer,
        "w",
        zipfile.ZIP_DEFLATED,
    ) as archive:
        archive.writestr(
            month_name,
            _make_month_zip(),
        )

    return buffer.getvalue()


def test_prepare_release_assets(
    monkeypatch,
    tmp_path,
):
    expected = [
        tmp_path
        / "NiftyOptions 2017.zip",
        tmp_path
        / "NiftyOptions 2017091.zip",
    ]

    def fake_download(
        owner,
        repo,
        tag,
        asset_names,
        destination_dir,
    ):
        assert owner == (
            "myswingbtsttrading"
        )
        assert repo == (
            "nifty-options-btst"
        )
        assert tag == (
            "data-2017-v1"
        )

        assert asset_names == [
            "NiftyOptions 2017.zip",
            "NiftyOptions 2017091.zip",
        ]

        return expected

    monkeypatch.setattr(
        release_btst_pipeline,
        "download_release_assets",
        fake_download,
    )

    result = (
        release_btst_pipeline.prepare_release_assets(
            tmp_path
        )
    )

    assert result == expected


def test_pipeline_downloads_and_runs_probe(
    monkeypatch,
    tmp_path,
):
    primary = (
        tmp_path
        / "NiftyOptions 2017.zip"
    )

    split = (
        tmp_path
        / "NiftyOptions 2017091.zip"
    )

    primary.write_bytes(
        _make_year_zip(
            "October 2017.zip"
        )
    )

    split.write_bytes(
        _make_year_zip(
            "November 2017.zip"
        )
    )

    def fake_prepare(
        destination_dir,
        owner,
        repo,
        tag,
        asset_names,
    ):
        return [
            primary,
            split,
        ]

    monkeypatch.setattr(
        release_btst_pipeline,
        "prepare_release_assets",
        fake_prepare,
    )

    result = (
        release_btst_pipeline.run_release_btst_pipeline(
            destination_dir=tmp_path,
            monthly_zip_name="November 2017.zip",
            option_type="PE",
            strike=10050,
            entry_date=date(
                2017,
                10,
                26,
            ),
            exit_date=date(
                2017,
                10,
                27,
            ),
        )
    )

    assert result["option_type"] == "PE"
    assert result["strike"] == 10050.0

    assert (
        result["entry"]["close"]
        == 55.55
    )

    assert (
        result["exit"]["close"]
        == 49.65
    )

    assert (
        result["release_owner"]
        == "myswingbtsttrading"
    )

    assert (
        result["release_repo"]
        == "nifty-options-btst"
    )

    assert (
        result["release_tag"]
        == "data-2017-v1"
    )

    assert set(
        result["downloaded_assets"]
    ) == {
        "NiftyOptions 2017.zip",
        "NiftyOptions 2017091.zip",
    }


def test_pipeline_allows_custom_release(
    monkeypatch,
    tmp_path,
):
    archive = (
        tmp_path
        / "NiftyOptions 2017.zip"
    )

    archive.write_bytes(
        _make_year_zip(
            "November 2017.zip"
        )
    )

    monkeypatch.setattr(
        release_btst_pipeline,
        "prepare_release_assets",
        lambda **kwargs: [archive],
    )

    result = (
        release_btst_pipeline.run_release_btst_pipeline(
            destination_dir=tmp_path,
            monthly_zip_name="November 2017.zip",
            option_type="PE",
            strike=10050,
            entry_date=date(
                2017,
                10,
                26,
            ),
            exit_date=date(
                2017,
                10,
                27,
            ),
            owner="example-owner",
            repo="example-repo",
            tag="example-tag",
            asset_names=[
                "NiftyOptions 2017.zip"
            ],
        )
    )

    assert (
        result["release_owner"]
        == "example-owner"
    )

    assert (
        result["release_repo"]
        == "example-repo"
    )

    assert (
        result["release_tag"]
        == "example-tag"
    )