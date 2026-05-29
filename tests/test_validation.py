import pytest

from validation import sanitize_action


def test_sanitize_action_rejects_xss_payloads():
    with pytest.raises(ValueError, match="HTML/script"):
        sanitize_action("<script>alert('x')</script>")


def test_sanitize_action_rejects_spammy_repeated_characters():
    with pytest.raises(ValueError, match="repeated"):
        sanitize_action("aaaaaaaaaaaaaaa")


def test_sanitize_action_truncates_long_input_after_stripping():
    result = sanitize_action(f"  {'walk north ' * 40}  ")

    assert len(result) == 300
    assert result.startswith("walk north")
    assert not result.startswith(" ")
