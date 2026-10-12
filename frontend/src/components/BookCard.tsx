
import type { Book } from "../api/books";

interface BookCardProps {
  book: Book;
  onViewChapters: (book: Book) => void;
  onContinueGeneration: (book: Book) => void;
}

function getStatusLabel(book: Book): string {
  if (
    book.chapter_count > 0 &&
    book.pending_chapter_count > 0
  ) {
    return "Partially generated";
  }

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
  onViewChapters,
  onContinueGeneration,
}: BookCardProps) {
  const createdDate = new Date(book.created_at);

  return (
    <article className="book-card">
      <div className="book-card-header">
        <h3>{book.title}</h3>

        <span className={`status status-${book.status}`}>
          {getStatusLabel(book)}
        </span>
      </div>

      <p className="book-filename">
        {book.original_filename}
      </p>

      <p className="book-date">
        Added {createdDate.toLocaleDateString()}
      </p>

      {book.chapter_count > 0 ? (
        <p className="book-chapter-summary">
          {book.completed_chapter_count} of{" "}
          {book.chapter_count} chapters ready
        </p>
      ) : (
        <p className="book-chapter-summary">
          Preparing chapters...
        </p>
      )}
      
      {book.pending_chapter_count > 0 && (
        <p className="book-chapter-pending">
          {book.pending_chapter_count} chapters pending
        </p>
      )}

      {book.pending_chapter_count > 0 && (
        <button
          type="button"
          className="button-secondary"
          onClick={() =>
            onContinueGeneration(book)
          }
        >
          Continue generation
        </button>
      )}

      {book.status === "processing" && (
        <div className="book-progress">
          <progress value={book.progress} max={100} />
          <span>{book.progress}%</span>
        </div>
      )}

      {book.chapter_count > 0 &&
        book.pending_chapter_count === 0 && (
          <div className="book-actions">
            <p className="ready-message">
              Audiobook ready. View the chapters to listen.
            </p>

            <button
              type="button"
              onClick={() => onViewChapters(book)}
            >
              View chapters
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