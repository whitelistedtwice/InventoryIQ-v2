import os
import pytest

from gemini_config import get_gemini_api_key, is_gemini_configured


def test_gemini_sdk_is_importable():
    try:
        from google import genai  # noqa: F401
    except ImportError as exc:
        pytest.fail(f"google-genai SDK is not installed or importable: {exc}")


def test_gemini_api_key_missing_when_not_set(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    if os.path.exists(".env"):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert get_gemini_api_key() is None
    assert is_gemini_configured() is False


def test_gemini_api_key_detected_when_set(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-value")
    assert get_gemini_api_key() == "test-key-value"
    assert is_gemini_configured() is True


def test_gemini_api_key_blank_is_treated_as_missing(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "   ")
    assert get_gemini_api_key() is None
    assert is_gemini_configured() is False


def test_gemini_api_key_not_leaked_in_config():
    key = get_gemini_api_key()
    if key is not None:
        pytest.fail("Real API key should not be present in test environment; got non-None key.")


def test_gemini_env_file_is_gitignored():
    with open(".gitignore", "r", encoding="utf-8") as f:
        gitignore = f.read()
    assert ".env" in gitignore.splitlines(), ".env must be listed in .gitignore"


def test_gemini_env_example_exists():
    assert os.path.exists(".env.example"), ".env.example should exist for Gemini setup guidance"


def test_gemini_env_example_does_not_contain_real_key():
    with open(".env.example", "r", encoding="utf-8") as f:
        content = f.read()
    assert "your_gemini_api_key_here" in content
    assert "AIza" not in content, "Real API key must not be committed in .env.example"


def test_gemini_config_importable():
    import gemini_config  # noqa: F401
