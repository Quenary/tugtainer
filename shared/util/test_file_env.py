import os

import pytest

from shared.util.file_env import apply_file_env


def test_reads_file_and_clears_file_var(tmp_path, monkeypatch):
    secret = tmp_path / "secret"
    secret.write_text("s3cret\n")
    monkeypatch.delenv("DEMO_SECRET", raising=False)
    monkeypatch.setenv("DEMO_SECRET_FILE", str(secret))

    apply_file_env(("DEMO_SECRET",))

    assert os.environ["DEMO_SECRET"] == "s3cret"
    assert os.environ["DEMO_SECRET_FILE"] == ""


def test_strips_crlf(tmp_path, monkeypatch):
    secret = tmp_path / "secret"
    secret.write_text("s3cret\r\n")
    monkeypatch.delenv("DEMO_SECRET", raising=False)
    monkeypatch.setenv("DEMO_SECRET_FILE", str(secret))

    apply_file_env(("DEMO_SECRET",))

    assert os.environ["DEMO_SECRET"] == "s3cret"


def test_leaves_plain_var_untouched(monkeypatch):
    monkeypatch.setenv("DEMO_SECRET", "from-env")
    monkeypatch.delenv("DEMO_SECRET_FILE", raising=False)

    apply_file_env(("DEMO_SECRET",))

    assert os.environ["DEMO_SECRET"] == "from-env"


def test_rejects_both_var_and_file(tmp_path, monkeypatch):
    secret = tmp_path / "secret"
    secret.write_text("from-file\n")
    monkeypatch.setenv("DEMO_SECRET", "from-env")
    monkeypatch.setenv("DEMO_SECRET_FILE", str(secret))

    with pytest.raises(RuntimeError, match="exclusive"):
        apply_file_env(("DEMO_SECRET",))


def test_rejects_missing_file(tmp_path, monkeypatch):
    missing = tmp_path / "missing"
    monkeypatch.delenv("DEMO_SECRET", raising=False)
    monkeypatch.setenv("DEMO_SECRET_FILE", str(missing))

    with pytest.raises(RuntimeError, match="not readable"):
        apply_file_env(("DEMO_SECRET",))


def test_second_apply_is_idempotent(tmp_path, monkeypatch):
    secret = tmp_path / "secret"
    secret.write_text("s3cret\n")
    monkeypatch.delenv("DEMO_SECRET", raising=False)
    monkeypatch.setenv("DEMO_SECRET_FILE", str(secret))

    apply_file_env(("DEMO_SECRET",))
    apply_file_env(("DEMO_SECRET",))

    assert os.environ["DEMO_SECRET"] == "s3cret"
    assert os.environ["DEMO_SECRET_FILE"] == ""
