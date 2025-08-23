from core.logger import escape_markdown_v2


def test_escape_markdown_v2():
    text = '_*[]()~`>#+-=|{}.!'
    escaped = escape_markdown_v2(text)
    expected = ''.join('\\' + c for c in text)
    assert escaped == expected
