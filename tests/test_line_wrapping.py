"""Tests for line wrapping functionality."""


from tia_portal_translator.pipeline import apply_line_wrapping


def test_apply_line_wrapping_wraps_long_lines():
    """Test that long translated text is wrapped to match source line length."""
    # Test with text that has natural break points (spaces)
    source_text = "short text here"  # 15 chars
    translated_text = "this is a much longer translated text that should wrap"  # 55 chars
    wrapped = apply_line_wrapping(translated_text, source_text, tolerance=1.2)
    # 15 * 1.2 = 18, and 55 > 18, so it should wrap at width=18
    assert "\n" in wrapped


def test_apply_line_wrapping_preserves_short_text():
    """Test that short text is not wrapped."""
    source_text = "Hello world"
    translated_text = "Hallo Welt"
    wrapped = apply_line_wrapping(translated_text, source_text, tolerance=1.2)
    assert "\n" not in wrapped
    assert wrapped == translated_text


def test_apply_line_wrapping_respects_tolerance():
    """Test that tolerance parameter controls when wrapping occurs."""
    source_text = "test"  # 4 chars
    translated_text = "testing one two three"  # 21 chars with spaces
    
    # With tolerance=1.2, 4*1.2=4.8, so 21>4.8 should wrap
    wrapped = apply_line_wrapping(translated_text, source_text, tolerance=1.2)
    assert "\n" in wrapped
    
    # With tolerance=10.0, 4*10.0=40, so 21<40 should NOT wrap
    not_wrapped = apply_line_wrapping(translated_text, source_text, tolerance=10.0)
    assert "\n" not in not_wrapped


def test_apply_line_wrapping_preserves_existing_newlines():
    """Test that existing line breaks in source are respected."""
    source_text = "line one\nline two"
    translated_text = "erste Zeile\nzweite Zeile"
    wrapped = apply_line_wrapping(translated_text, source_text, tolerance=1.2)
    assert wrapped.count("\n") >= 1  # At least the original newline


def test_apply_line_wrapping_handles_empty_text():
    """Test that empty strings are handled gracefully."""
    source_text = ""
    translated_text = ""
    wrapped = apply_line_wrapping(translated_text, source_text, tolerance=1.2)
    assert wrapped == ""


def test_apply_line_wrapping_no_break_on_words():
    """Test that words are not broken mid-word (break_long_words=False)."""
    source_text = "short"  # 5 chars
    # Single long word with no spaces - should not be broken
    translated_text = "supercalifragilisticexpialidocious"  # 34 chars
    wrapped = apply_line_wrapping(translated_text, source_text, tolerance=1.2)
    # Should not add newlines because can't break the word
    assert "\n" not in wrapped
