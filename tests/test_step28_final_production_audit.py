from pathlib import Path
import ast


ROOT = Path(__file__).resolve().parents[1]


def _read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def _parse(path):
    return ast.parse(_read(path))


def _function_source(path, name):
    tree = _parse(path)
    lines = _read(path).splitlines()

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return "\n".join(lines[node.lineno - 1 : node.end_lineno])

    raise AssertionError(f"Function {name!r} not found in {path}")


def test_required_production_files_exist():
    required = [
        "main.py",
        "nse_live_data.py",
        "live_market_data.py",
        "yahoo_nifty_data.py",
        "notifier.py",
        ".github/workflows/btst_3pm.yml",
        ".github/workflows/btst_915.yml",
    ]

    missing = [path for path in required if not (ROOT / path).exists()]
    assert not missing, f"Missing production files: {missing}"


def test_main_is_valid_python():
    _parse("main.py")


def test_live_data_modules_are_valid_python():
    _parse("nse_live_data.py")
    _parse("live_market_data.py")
    _parse("yahoo_nifty_data.py")


def test_main_uses_send_alert():
    source = _read("main.py")

    assert "from notifier import send_alert" in source
    assert "send_telegram" not in source


def test_3pm_checks_duplicate_position_before_formatting():
    source = _function_source("main.py", "run_3pm")

    duplicate_pos = source.find("STATE_FILE.exists()")
    format_pos = source.find("_format_signal_message")

    assert duplicate_pos >= 0
    assert format_pos >= 0
    assert duplicate_pos < format_pos


def test_3pm_saves_state_before_alert():
    source = _function_source("main.py", "run_3pm")

    save_pos = source.find("_save_signal_state")
    alert_pos = source.find("send_alert")

    assert save_pos >= 0
    assert alert_pos >= 0
    assert save_pos < alert_pos


def test_3pm_rolls_back_state_when_alert_fails():
    source = _function_source("main.py", "run_3pm")

    alert_pos = source.find("send_alert")
    remove_pos = source.find("_remove_active_state", alert_pos)

    assert alert_pos >= 0
    assert remove_pos >= 0


def test_930_checks_completed_exit_before_fetching_chain():
    source = _function_source("main.py", "run_930")

    idempotency_pos = source.find("_exit_record_matches_position")

    chain_markers = [
        "fetch_option_chain",
        "_build_option_chain",
        "get_option_chain",
        "option_chain",
        "find_option_quote",
    ]

    chain_positions = [
        source.find(marker)
        for marker in chain_markers
        if source.find(marker) >= 0
    ]

    assert idempotency_pos >= 0
    assert chain_positions

    first_chain_pos = min(chain_positions)
    assert idempotency_pos < first_chain_pos


def test_930_saves_exit_before_alert():
    source = _function_source("main.py", "run_930")

    save_pos = source.find("_save_exit_record")
    alert_pos = source.find("send_alert")

    assert save_pos >= 0
    assert alert_pos >= 0
    assert save_pos < alert_pos


def test_930_removes_state_only_after_successful_alert():
    source = _function_source("main.py", "run_930")

    alert_pos = source.find("send_alert")
    remove_pos = source.find("_remove_active_state", alert_pos)

    assert alert_pos >= 0
    assert remove_pos >= 0


def test_exit_record_matching_is_case_insensitive():
    source = _function_source("main.py", "_exit_record_matches_position")

    assert (
        ".upper()" in source
        or ".lower()" in source
        or ".casefold()" in source
    )


def test_atomic_json_write_is_used():
    source = _read("main.py")

    assert "def _atomic_write_json" in source
    assert "os.replace" in source


def test_workflows_have_write_permission():
    for path in (
        ".github/workflows/btst_3pm.yml",
        ".github/workflows/btst_915.yml",
    ):
        source = _read(path)

        assert "permissions:" in source
        assert "contents: write" in source


def test_workflows_have_concurrency_protection():
    for path in (
        ".github/workflows/btst_3pm.yml",
        ".github/workflows/btst_915.yml",
    ):
        source = _read(path)

        assert "concurrency:" in source


def test_workflows_have_timeout_protection():
    for path in (
        ".github/workflows/btst_3pm.yml",
        ".github/workflows/btst_915.yml",
    ):
        source = _read(path)

        assert "timeout-minutes:" in source


def test_3pm_workflow_runs_at_1500_ist():
    source = _read(".github/workflows/btst_3pm.yml")

    assert 'cron: "30 9 * * 1-5"' in source


def test_930_workflow_runs_at_0930_ist():
    source = _read(".github/workflows/btst_915.yml")

    assert 'cron: "0 4 * * 1-5"' in source


def test_required_telegram_secrets_are_referenced():
    workflow_sources = [
        _read(".github/workflows/btst_3pm.yml"),
        _read(".github/workflows/btst_915.yml"),
    ]

    combined = "\n".join(workflow_sources)

    assert "TELEGRAM_TOKEN" in combined
    assert "TELEGRAM_CHAT_ID" in combined


def test_no_hardcoded_telegram_credentials():
    for path in ("main.py", "notifier.py"):
        source = _read(path)

        assert "TELEGRAM_TOKEN =" not in source
        assert "TELEGRAM_CHAT_ID =" not in source


def test_run_915_delegates_to_run_930():
    source = _function_source("main.py", "run_915")

    assert "run_930(" in source


def test_option_contract_validation_exists():
    source = _read("main.py")

    assert "option_type" in source
    assert "strike" in source
    assert "expiry" in source
    assert "find_option_quote" in source


def test_positive_exit_premium_is_required():
    source = _function_source("main.py", "run_930")

    assert "exit_price" in source
    assert "> 0" in source or "positive" in source.lower()


def test_completed_exit_contains_closed_status():
    source = _read("main.py")

    assert '"status": "CLOSED"' in source or "'status': 'CLOSED'" in source