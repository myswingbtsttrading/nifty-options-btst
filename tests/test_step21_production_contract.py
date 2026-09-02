from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path):
    return path.read_text(encoding="utf-8")


def test_requirements_contains_runtime_dependencies():
    requirements = _read(ROOT / "requirements.txt")

    assert "requests" in requirements
    assert "yfinance" in requirements
    assert "pandas" in requirements


def test_3pm_workflow_uses_correct_schedule():
    workflow = _read(
        ROOT / ".github" / "workflows" / "btst_3pm.yml"
    )

    assert 'cron: "30 9 * * 1-5"' in workflow
    assert "python main.py --mode 3pm" in workflow
    assert "TELEGRAM_TOKEN" in workflow
    assert "TELEGRAM_CHAT_ID" in workflow


def test_930_workflow_uses_correct_schedule():
    workflow = _read(
        ROOT / ".github" / "workflows" / "btst_915.yml"
    )

    assert 'cron: "0 4 * * 1-5"' in workflow
    assert "python main.py --mode 930" in workflow
    assert "TELEGRAM_TOKEN" in workflow
    assert "TELEGRAM_CHAT_ID" in workflow


def test_workflows_have_write_permission():
    for filename in (
        "btst_3pm.yml",
        "btst_915.yml",
    ):
        workflow = _read(
            ROOT / ".github" / "workflows" / filename
        )

        assert "permissions:" in workflow
        assert "contents: write" in workflow


def test_3pm_workflow_runs_tests_before_live_signal():
    workflow = _read(
        ROOT / ".github" / "workflows" / "btst_3pm.yml"
    )

    assert workflow.index(
        "Run test suite"
    ) < workflow.index(
        "Generate 3 PM BTST signal"
    )


def test_930_workflow_runs_tests_before_live_exit():
    workflow = _read(
        ROOT / ".github" / "workflows" / "btst_915.yml"
    )

    assert workflow.index(
        "Run test suite"
    ) < workflow.index(
        "Generate 9:30 AM SELL alert"
    )


def test_3pm_workflow_persists_active_state():
    workflow = _read(
        ROOT / ".github" / "workflows" / "btst_3pm.yml"
    )

    assert "live_btst_signal.json" in workflow
    assert "git add" in workflow
    assert "git commit" in workflow
    assert "git push" in workflow


def test_930_workflow_persists_exit_record():
    workflow = _read(
        ROOT / ".github" / "workflows" / "btst_915.yml"
    )

    assert "last_btst_exit.json" in workflow
    assert "git add" in workflow
    assert "git commit" in workflow
    assert "git push" in workflow


def test_workflows_use_python_312():
    for filename in (
        "btst_3pm.yml",
        "btst_915.yml",
    ):
        workflow = _read(
            ROOT / ".github" / "workflows" / filename
        )

        assert 'python-version: "3.12"' in workflow


def test_workflows_install_requirements():
    for filename in (
        "btst_3pm.yml",
        "btst_915.yml",
    ):
        workflow = _read(
            ROOT / ".github" / "workflows" / filename
        )

        assert "pip install -r requirements.txt" in workflow


def test_main_exposes_all_production_modes():
    main_source = _read(
        ROOT / "main.py"
    )

    assert '"3pm"' in main_source
    assert '"930"' in main_source
    assert '"915"' in main_source
    assert '"smoke"' in main_source


def test_main_has_state_and_exit_files():
    main_source = _read(
        ROOT / "main.py"
    )

    assert 'STATE_FILE = DATA_DIR / "live_btst_signal.json"' in main_source
    assert 'EXIT_FILE = DATA_DIR / "last_btst_exit.json"' in main_source


def test_main_has_atomic_state_persistence():
    main_source = _read(
        ROOT / "main.py"
    )

    assert "def _atomic_write_json" in main_source
    assert "os.replace(" in main_source
    assert ".tmp" in main_source


def test_main_validates_stored_position():
    main_source = _read(
        ROOT / "main.py"
    )

    assert "def _load_signal_state" in main_source
    assert '"decision"' in main_source
    assert '"direction"' in main_source
    assert '"expiry"' in main_source
    assert '"strike"' in main_source
    assert '"option_type"' in main_source
    assert '"entry_price"' in main_source
    assert '"quantity"' in main_source
    assert '"lots"' in main_source


def test_main_requires_closed_exit_for_idempotency():
    main_source = _read(
        ROOT / "main.py"
    )

    assert "def _exit_record_matches_position" in main_source
    assert 'get("status", "")' in main_source
    assert '"CLOSED"' in main_source


def test_main_uses_exact_contract_for_exit():
    main_source = _read(
        ROOT / "main.py"
    )

    assert "find_option_quote(" in main_source
    assert "expiry=expiry" in main_source
    assert "strike=strike" in main_source
    assert "option_type=option_type" in main_source


def test_main_persists_exit_before_telegram():
    main_source = _read(
        ROOT / "main.py"
    )

    save_position = main_source.index(
        "_save_exit_record("
    )
    telegram = main_source.index(
        "send_alert(message)"
    )

    assert save_position < telegram


def test_main_removes_state_after_successful_telegram():
    main_source = _read(
        ROOT / "main.py"
    )

    telegram = main_source.index(
        "send_alert(message)"
    )
    remove_state = main_source.index(
        "_remove_active_state()"
    )

    assert telegram < remove_state