
import type { Book } from "../api/books";

interface BookCardProps {
  book: Book;
  onViewChapters: (book: Book) => void;
  onContinueGeneration: (book: Book) => void;
  onDeleteBook: (book: Book) => void;
}


function isAudiobookReady(book: Book): boolean {
  return (
    book.chapter_count > 0 &&
    book.completed_chapter_count === book.chapter_count
  );
}

function canContinueGeneration(book: Book): boolean {
  return (
    book.pending_chapter_count > 0 &&
    ["paused", "completed", "failed"].includes(book.status)
  );
}

function getStatusLabel(book: Book): string {
  switch (book.status) {
    case "queued":
      return book.stage === "queued_resume"
        ? "Queued to resume"
        : "Queued";

    case "processing": {
      const stageLabels: Record<string, string> = {
        extracting: "Extracting text",
        chunking: "Preparing chapters",
        generating_audio: "Generating audio",
        assembling: "Finalizing audiobook",
      };

      return stageLabels[book.stage] ?? book.stage;
    }

    case "paused":
      return "Paused";

    case "failed":
      return "Processing failed";

    case "completed":
      if (isAudiobookReady(book)) {
        return "Audiobook ready";
      }

      return book.chapter_count > 0
        ? "Partially generated"
        : "Preparing chapters";

    default:
      return book.status;
  }
}


function BookCard({
  book,
  onViewChapters,
  onContinueGeneration,
  onDeleteBook,
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

      {canContinueGeneration(book) && (
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

      {book.chapter_count > 0 && (
        <div className="book-actions">
          <p className="ready-message">
            {isAudiobookReady(book)
              ? "Audiobook ready. View the chapters to listen."
              : book.completed_chapter_count > 0
                ? "Completed chapters are ready to play."
                : "View chapter generation progress."}
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
      
      <div className="book-delete-action">
      <button
        type="button"
        className="button-secondary"
        onClick={() => onDeleteBook(book)}
      >
        Delete book
      </button>
    </div>
    </article>
  );
}

export default BookCard;