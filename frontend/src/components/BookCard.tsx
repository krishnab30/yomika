import type { Book } from "../api/books";

interface BookCardProps {
  book: Book;
  onPlay: (book: Book) => void;
}

function getStatusLabel(book: Book): string {
  switch (book.status) {
    case "queued":
      return "Queued";

    case "processing":
      return book.stage;

    case "completed":
      return "Audiobook ready";

    case "failed":
      return "Processing failed";

    default:
      return book.status;
  }
}

function BookCard({
  book,
  onPlay,
}: BookCardProps) {
  const createdDate =
    new Date(book.created_at);

  return (
    <article className="book-card">
      <div className="book-card-header">
        <h3>{book.title}</h3>

        <span
          className={`status status-${book.status}`}
        >
          {getStatusLabel(book)}
        </span>
      </div>

      <p className="book-filename">
        {book.original_filename}
      </p>

      <p className="book-date">
        Added{" "}
        {createdDate.toLocaleDateString()}
      </p>

      {book.status === "processing" && (
        <div className="book-progress">
          <progress
            value={book.progress}
            max={100}
          />

          <span>
            {book.progress}%
          </span>
        </div>
      )}

    {book.status === "completed" && (
    <div className="book-actions">
        <p className="ready-message">
        Audiobook ready to play.
        </p>

        <button
        type="button"
        onClick={() => onPlay(book)}
        >
        Play audiobook
        </button>
    </div>
    )}
      {book.status === "failed" && (
        <p className="error-message">
          {book.message}
        </p>
      )}
    </article>
  );
}

export default BookCard;