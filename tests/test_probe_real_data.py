from datetime import date
from pathlib import Path
import zipfile

from probe_real_data import main


def test_probe_cli_with_realistic_archive(
    tmp_path,
    monkeypatch,
    capsys,
):
    monthly_zip = tmp_path / "November 2017.zip"

    monthly_data = (
        "PE 10050,2017/10/26,14:59,"
        "55,56,54,55.00,100\n"
        "PE 10050,2017/10/26,15:00,"
        "55,56,54,55.55,100\n"
        "PE 10050,2017/10/27,09:15,"
        "49,50,48,49.65,100\n"
    )

    monthly_buffer = tmp_path / "monthly.zip"

    with zipfile.ZipFile(
        monthly_buffer,
        "w",
        zipfile.ZIP_DEFLATED,
    ) as archive:
        archive.writestr(
            "PE 10050.txt",
            monthly_data,
        )

    year_zip = tmp_path / "NiftyOptions 2017.zip"

    with zipfile.ZipFile(
        year_zip,
        "w",
        zipfile.ZIP_DEFLATED,
    ) as archive:
        archive.write(
            monthly_buffer,
            "November 2017.zip",
        )

    monkeypatch.setattr(
        "sys.argv",
        [
            "probe_real_data.py",
            str(year_zip),
        ],
    )

    result = main()

    captured = capsys.readouterr()

    assert result == 0
    assert "ZENODO REAL-DATA CONTRACT PROBE" in captured.out
    assert "PE 10050" in captured.out
    assert "2017-11-30" in captured.out
    assert "₹55.55" in captured.out
    assert "₹49.65" in captured.out
    assert "STATUS: PASS" in captured.out