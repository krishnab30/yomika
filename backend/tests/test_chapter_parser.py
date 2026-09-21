from backend.app.services.chapter_parser import parse_chapters


def test_parse_chapters() -> None:
    text = """Chapter 1: Floating Fortress

First paragraph.

Second paragraph.

Chapter 2: An Audience with Perugius

Another paragraph.

Extra Chapter: The Birth of a New Sword King

Final paragraph.
"""

    chapters = parse_chapters(text)

    assert len(chapters) == 3

    assert chapters[0].number == 1
    assert chapters[0].title == "Floating Fortress"

    assert chapters[1].number == 2
    assert (
        chapters[1].title
        == "An Audience with Perugius"
    )

    assert chapters[2].number is None
    assert (
        chapters[2].title
        == "The Birth of a New Sword King"
    )

    assert (
        chapters[0].display_title
        == "Chapter 1: Floating Fortress"
    )

    assert (
        chapters[2].display_title
        == "Extra Chapter: The Birth of a New Sword King"
    )