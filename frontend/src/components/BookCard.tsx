import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { getM4BDownloadUrl, type Book } from "../api/books";

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

function getExportUnavailableMessage(book: Book): string {
  switch (book.status) {
    case "queued":
    case "processing":
      return (
        "Generation is still in progress. You can listen to completed chapters now, " +
        "but the full audiobook export unlocks only after every chapter has finished."
      );

    case "paused":
      return (
        "Generation is paused with chapters still unfinished. Resume generation " +
        "to finish the remaining chapters; the full audiobook export will unlock " +
        "when every chapter is ready."
      );

    case "failed":
      return (
        "Generation stopped before every chapter was completed. Continue generation " +
        "when you're ready. The full audiobook export will be available once all " +
        "chapters have finished successfully."
      );

    default:
      return (
        "This book has only been generated partially. The full audiobook export " +
        "requires completed audio for every chapter."
      );
  }
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
  const [isExportModalOpen, setIsExportModalOpen] = useState(false);
  const closeModalButtonRef = useRef<HTMLButtonElement>(null);
  const unavailableExportButtonRef = useRef<HTMLButtonElement>(null);
  const exportModalRef = useRef<HTMLElement>(null);
  const createdDate = new Date(book.created_at);
  const audiobookReady = isAudiobookReady(book);
  const remainingChapterCount = Math.max(
    book.chapter_count - book.completed_chapter_count,
    0,
  );
  const exportProgress = book.chapter_count > 0
    ? Math.min(
        100,
        Math.round((book.completed_chapter_count / book.chapter_count) * 100),
      )
    : 0;

  useEffect(() => {
    if (!isExportModalOpen) {
      return;
    }

    const previousBodyOverflow = document.body.style.overflow;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setIsExportModalOpen(false);
        return;
      }

      if (event.key === "Tab") {
        const focusableElements = exportModalRef.current?.querySelectorAll<HTMLElement>(
          'button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
        );

        if (!focusableElements?.length) {
          return;
        }

        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];

        if (event.shiftKey && document.activeElement === firstElement) {
          event.preventDefault();
          lastElement.focus();
        } else if (!event.shiftKey && document.activeElement === lastElement) {
          event.preventDefault();
          firstElement.focus();
        }
      }
    };

    document.body.style.overflow = "hidden";
    document.addEventListener("keydown", handleKeyDown);
    closeModalButtonRef.current?.focus();

    return () => {
      document.body.style.overflow = previousBodyOverflow;
      document.removeEventListener("keydown", handleKeyDown);
      unavailableExportButtonRef.current?.focus();
    };
  }, [isExportModalOpen]);

  const closeExportModal = () => setIsExportModalOpen(false);

  return (
    <>
      <article className="book-card">
        <div className="book-card-header">
          <h3>{book.title}</h3>

          <span className={`status status-${book.status}`}>
            {getStatusLabel(book)}
          </span>
        </div>

        <p className="book-filename">{book.original_filename}</p>

        <p className="book-date">
          Added {createdDate.toLocaleDateString()}
        </p>

        {book.chapter_count > 0 ? (
          <p className="book-chapter-summary">
            {book.completed_chapter_count} of {" "}
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
            onClick={() => onContinueGeneration(book)}
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
              {audiobookReady
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

            {audiobookReady ? (
              <a
                className="book-download-m4b-link"
                href={getM4BDownloadUrl(book.id)}
              >
                Download full audiobook (.m4b)
              </a>
            ) : (
              <button
                type="button"
                ref={unavailableExportButtonRef}
                className="book-download-m4b-link book-download-m4b-unavailable"
                onClick={() => setIsExportModalOpen(true)}
                aria-haspopup="dialog"
              >
                Full audiobook not ready
              </button>
            )}
          </div>
        )}

        {book.status === "failed" && (
          <p className="error-message">{book.message}</p>
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

      {isExportModalOpen && createPortal(
        <div className="audiobook-export-modal-backdrop">
          <section
            ref={exportModalRef}
            className="audiobook-export-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="audiobook-export-modal-title"
            aria-describedby="audiobook-export-modal-description"
          >
            <div className="audiobook-export-modal-header">
              <p className="audiobook-export-modal-eyebrow">
                FULL AUDIOBOOK EXPORT
              </p>
              <button
                ref={closeModalButtonRef}
                type="button"
                className="audiobook-export-close-button"
                onClick={closeExportModal}
                aria-label="Close export information"
              >
                ×
              </button>
            </div>

            <h2 id="audiobook-export-modal-title">
              Not ready just yet
            </h2>

            <p id="audiobook-export-modal-description">
              {getExportUnavailableMessage(book)}
            </p>

            <div className="audiobook-export-progress">
              <div className="audiobook-export-progress-label">
                <span>Chapter audio ready</span>
                <strong>
                  {book.completed_chapter_count} / {book.chapter_count}
                </strong>
              </div>
              <progress
                value={book.completed_chapter_count}
                max={book.chapter_count}
                aria-label={`${exportProgress}% of chapter audio ready`}
              />
              <p>
                {remainingChapterCount === 1
                  ? "1 chapter still needs to finish."
                  : `${remainingChapterCount} chapters still need to finish.`}
              </p>
            </div>

            <div className="audiobook-export-note">
              Your completed chapters are still available to listen to individually.
            </div>

            <div className="audiobook-export-actions">
              {canContinueGeneration(book) && (
                <button
                  type="button"
                  className="audiobook-export-continue-button"
                  onClick={() => {
                    closeExportModal();
                    onContinueGeneration(book);
                  }}
                >
                  Continue generation
                </button>
              )}
              <button
                type="button"
                className="audiobook-export-secondary-button"
                onClick={() => {
                  closeExportModal();
                  onViewChapters(book);
                }}
              >
                View chapters
              </button>
              <button
                type="button"
                className="audiobook-export-dismiss-button"
                onClick={closeExportModal}
              >
                Got it
              </button>
            </div>
          </section>
        </div>,
        document.body,
      )}
    </>
  );
}

export default BookCard;
