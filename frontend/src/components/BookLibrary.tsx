import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

import {
  getBooks,
  type Book,
  type Chapter,
} from "../api/books";

import BookCard from "./BookCard";
import ChapterList from "./ChapterList";

interface BookLibraryProps {
  refreshKey: number;
  activeGenerationIds: string[];
  onGenerationFinished: (bookId: string) => void;
  onPlayChapter: (
    book: Book,
    chapter: Chapter,
    chapters: Chapter[],
  ) => void;
  onContinueGeneration: (book: Book) => void;
  onDeleteBook: (book: Book) => void;
  onChaptersUpdated: (
  bookId: string,
  chapters: Chapter[],
) => void;
}

function BookLibrary({
  refreshKey,
  activeGenerationIds,
  onGenerationFinished,
  onPlayChapter,
  onContinueGeneration,
  onDeleteBook,
  onChaptersUpdated,
}: BookLibraryProps) {
  const [books, setBooks] = useState<Book[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedBook, setSelectedBook] = useState<Book | null>(null);
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const chapterPanelRef = useRef<HTMLElement | null>(null);

  const selectedBookId = selectedBook?.id;

  const handleChaptersLoaded = useCallback(
    (loadedChapters: Chapter[]) => {
      setChapters(loadedChapters);

      if (selectedBookId) {
        onChaptersUpdated(
          selectedBookId,
          loadedChapters,
        );
      }
    },
    [selectedBookId, onChaptersUpdated],
  );

  useEffect(() => {
    let cancelled = false;
    let pollTimeout: ReturnType<typeof setTimeout> | null = null;

    const loadBooks = async (showLoading: boolean) => {
      try {
        if (showLoading) {
          setIsLoading(true);
          setError(null);
        }

        const result = await getBooks();

        if (cancelled) {
          return;
        }

        setBooks(result);

        setSelectedBook((currentBook) => {
          if (!currentBook) {
            return null;
          }

          return (
            result.find(
              (book) => book.id === currentBook.id,
            ) ?? null
          );
        });

        const activeIds = new Set(
          activeGenerationIds,
        );

        const activeBooks = result.filter(
          (book) => activeIds.has(book.id),
        );

        const stillActive = activeBooks.filter(
          (book) =>
            book.status === "queued" ||
            book.status === "processing",
        );

        const finishedBooks = activeBooks.filter(
          (book) =>
            book.status !== "queued" &&
            book.status !== "processing",
        );

        for (const book of finishedBooks) {
          onGenerationFinished(book.id);
        }

        if (stillActive.length > 0) {
          pollTimeout = setTimeout(() => {
            void loadBooks(false);
          }, 2000);
        }
      } catch (loadError) {
        if (cancelled) {
          return;
        }

        const message =
          loadError instanceof Error
            ? loadError.message
            : "Failed to load books.";

        setError(message);

        for (const bookId of activeGenerationIds) {
          onGenerationFinished(bookId);
        }
      } finally {
        if (!cancelled && showLoading) {
          setIsLoading(false);
        }
      }
    };

    void loadBooks(true);

    return () => {
      cancelled = true;

      if (pollTimeout !== null) {
        clearTimeout(pollTimeout);
      }
    };
  }, [
    refreshKey,
    activeGenerationIds,
    onGenerationFinished,
  ]);

  useEffect(() => {
    if (!selectedBook || chapters.length === 0) {
      return;
    }

    const chapterListHeader =
      chapterPanelRef.current?.querySelector<HTMLElement>(
        ".chapter-list-header",
      );

    chapterListHeader?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  }, [selectedBook?.id, chapters.length]);

  const handleViewChapters = (book: Book) => {
    setSelectedBook(book);
    setChapters([]);
  };

  const handleCloseChapters = () => {
    setSelectedBook(null);
    setChapters([]);
  };

  return (
    <section className="library">
      <div className="library-header">
        <h2>Your Library</h2>

        <span>
          {books.length} {books.length === 1 ? "book" : "books"}
        </span>
      </div>

      {isLoading && <p>Loading your library...</p>}

      {error && (
        <p className="error-message">
          {error}
        </p>
      )}

      {!isLoading && !error && books.length === 0 && (
        <p>
          Your library is empty. Upload a PDF to get started.
        </p>
      )}

      {!isLoading && !error && books.length > 0 && (
        <div className="book-grid">
          {books.map((book) => (
            <BookCard
              key={book.id}
              book={book}
              onViewChapters={handleViewChapters}
              onContinueGeneration={onContinueGeneration}
              onDeleteBook={onDeleteBook}
            />
          ))}
        </div>
      )}

      {selectedBook && (
        <section className="chapter-panel" ref={chapterPanelRef}>
          <div className="chapter-panel-header">
            <h2>{selectedBook.title}</h2>

            <button
              type="button"
              onClick={handleCloseChapters}
            >
              Close chapters
            </button>
          </div>

          <ChapterList
            bookId={selectedBook.id}
            bookStatus={selectedBook.status}
            onChaptersLoaded={handleChaptersLoaded}
            onPlayChapter={(chapter) => {
              onPlayChapter(selectedBook, chapter, chapters);
            }}
          />
        </section>
      )}
    </section>
  );
}

export default BookLibrary;
