
import { useEffect, useState } from "react";
import { getChapters, type Chapter } from "../api/books";

function getChapterStatusLabel(status: string): string {
  switch (status) {
    case "completed":
      return "Completed";

    case "processing":
      return "Processing";

    case "pending":
      return "Pending";

    case "failed":
      return "Failed";

    default:
      return status;
  }
}

interface ChapterListProps {
  bookId: string;
  onPlayChapter: (chapter: Chapter) => void;
  onChaptersLoaded: (chapters: Chapter[]) => void;
}

function formatDuration(seconds: number | null): string {
  if (seconds === null || !Number.isFinite(seconds)) {
    return "";
  }

  const totalMinutes = Math.floor(seconds / 60);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;

  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  }

  return `${minutes}m`;
}

function getChapterLabel(chapter: Chapter): string {
  if (chapter.chapter_number === null) {
    return chapter.title;
  }

  return `Chapter ${chapter.chapter_number}: ${chapter.title}`;
}

// deprecated component
// function getStatusLabel(status: string): string {
//   switch (status) {
//     case "completed":
//       return "Ready";
//     case "processing":
//       return "Generating";
//     case "failed":
//       return "Failed";
//     case "pending":
//       return "Pending";
//     default:
//       return status;
//   }
// }

export default function ChapterList({
  bookId,
  onPlayChapter,
  onChaptersLoaded,
}: ChapterListProps) {
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadChapters() {
      setIsLoading(true);

      try {
        const result = await getChapters(bookId);

        if (!cancelled) {
          setChapters(result);
          setError(null);
          onChaptersLoaded(result);
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error
              ? err.message
              : "Failed to load chapters.",
          );
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    void loadChapters();

    return () => {
      cancelled = true;
    };
  }, [bookId, onChaptersLoaded]);

  if (isLoading) {
    return <p>Loading chapters...</p>;
  }

  if (error) {
    return (
      <div>
        <p role="alert">Could not load chapters: {error}</p>
      </div>
    );
  }

  if (chapters.length === 0) {
    return <p>No chapters found for this book.</p>;
  }

  const completedCount = chapters.filter(
    (chapter) => chapter.status === "completed",
  ).length;

  return (
    <section aria-label="Chapter list">
      <div>
        <h3>Chapters</h3>
        <p>
          {completedCount} of {chapters.length} chapters ready
        </p>
      </div>

      <ol>
        {chapters.map((chapter) => {
          const isCompleted = chapter.status === "completed";
          const duration = formatDuration(chapter.duration_seconds);

          return (
            <li key={chapter.id}>
              <div>
                <div>
                  <strong>{getChapterLabel(chapter)}</strong>
                </div>

                <div>
                  <span className={`chapter-status chapter-status-${chapter.status}`}
                  >
                    {getChapterStatusLabel(chapter.status)}
                  </span>
                  {duration && <span> · {duration}</span>}
                </div>
              </div>

              <button
                type="button"
                disabled={!isCompleted}
                onClick={() => onPlayChapter(chapter)}
              >
                Play
              </button>
            </li>
          );
        })}
      </ol>
    </section>
  );
}