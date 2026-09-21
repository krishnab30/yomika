from backend.app.services.chapter_parser import Chapter
from backend.app.services.text_chunker import chunk_chapter


def test_small_paragraphs_are_grouped() -> None:
    chapter = Chapter(
        number=1,
        title="Test",
        content=(
            "First paragraph.\n\n"
            "Second paragraph.\n\n"
            "Third paragraph."
        ),
    )

    chunks = chunk_chapter(
        chapter,
        target_characters=100,
        max_characters=150,
    )

    assert len(chunks) == 1
    assert "First paragraph." in chunks[0].text
    assert "Second paragraph." in chunks[0].text
    assert "Third paragraph." in chunks[0].text


def test_large_content_is_split() -> None:
    chapter = Chapter(
        number=1,
        title="Test",
        content=(
            "This is sentence one. "
            "This is sentence two. "
            "This is sentence three. "
            "This is sentence four."
        ),
    )

    chunks = chunk_chapter(
        chapter,
        target_characters=45,
        max_characters=60,
    )

    assert len(chunks) > 1

    for chunk in chunks:
        assert chunk.character_count <= 60