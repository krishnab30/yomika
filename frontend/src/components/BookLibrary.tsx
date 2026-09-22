import {
  useEffect,
  useState,
} from "react";

import {
  getBooks,
  type Book,
} from "../api/books";

import BookCard from "./BookCard";

interface BookLibraryProps {
  refreshKey: number;
  onPlayBook: (book: Book) => void;
}

function BookLibrary({
  refreshKey,
  onPlayBook,
}: BookLibraryProps) {
  const [books, setBooks] =
    useState<Book[]>([]);

  const [isLoading, setIsLoading] =
    useState(true);

  const [error, setError] =
    useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const loadBooks = async () => {
      try {
        setIsLoading(true);
        setError(null);

        const result = await getBooks();

        if (cancelled) {
          return;
        }

        setBooks(result);
      } catch (loadError) {
        if (cancelled) {
          return;
        }

        const message =
          loadError instanceof Error
            ? loadError.message
            : "Failed to load books.";

        setError(message);
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    };

    loadBooks();

    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  return (
    <section className="library">
      <div className="library-header">
        <h2>Your Library</h2>

        <span>
          {books.length}{" "}
          {books.length === 1
            ? "book"
            : "books"}
        </span>
      </div>

      {isLoading && (
        <p>Loading your library...</p>
      )}

      {error && (
        <p className="error-message">
          {error}
        </p>
      )}

      {!isLoading &&
        !error &&
        books.length === 0 && (
          <p>
            Your library is empty. Upload a
            PDF to get started.
          </p>
        )}

      {!isLoading &&
        !error &&
        books.length > 0 && (
          <div className="book-grid">
            {books.map((book) => (
              <BookCard
                key={book.id}
                book={book}
                onPlay={onPlayBook}
              />
            ))}
          </div>
        )}
    </section>
  );
}

export default BookLibrary;