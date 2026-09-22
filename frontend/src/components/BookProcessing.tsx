import {
  useEffect,
  useState,
} from "react";

import {
  getBookStatus,
  type BookStatusResponse,
} from "../api/books";

interface BookProcessingProps {
  bookId: string;
  onComplete: () => void;
}

function getStageLabel(stage: string): string {
  switch (stage) {
    case "queued":
      return "Queued";

    case "extracting":
      return "Reading PDF";

    case "normalizing":
      return "Cleaning text";

    case "chunking":
      return "Preparing narration";

    case "generating_audio":
      return "Generating audio";

    case "assembling":
      return "Assembling audiobook";

    case "completed":
      return "Audiobook ready";

    case "failed":
      return "Processing failed";

    default:
      return stage;
  }
}

function BookProcessing({
  bookId,
  onComplete,
}: BookProcessingProps) {
  const [status, setStatus] =
    useState<BookStatusResponse | null>(
      null,
    );

  const [error, setError] =
    useState<string | null>(null);

  useEffect(() => {
    let stopped = false;
    let timeoutId:
      ReturnType<typeof setTimeout> | undefined;

    const poll = async () => {
      try {
        const result =
          await getBookStatus(bookId);

        if (stopped) {
          return;
        }

        setStatus(result);
        setError(null);

        if (result.status === "completed") {
          onComplete();
          return;
        }

        if (result.status === "failed") {
          setError(
            result.message ||
              "Audiobook generation failed.",
          );
          return;
        }

        timeoutId = setTimeout(
          poll,
          2000,
        );
      } catch (pollError) {
        if (stopped) {
          return;
        }

        const message =
          pollError instanceof Error
            ? pollError.message
            : "Unable to fetch processing status.";

        setError(message);

        timeoutId = setTimeout(
          poll,
          3000,
        );
      }
    };

    poll();

    return () => {
      stopped = true;

      if (timeoutId !== undefined) {
        clearTimeout(timeoutId);
      }
    };
  }, [bookId, onComplete]);

  if (error) {
    return (
      <section>
        <h2>Something went wrong</h2>

        <p>{error}</p>
      </section>
    );
  }

  if (!status) {
    return (
      <section>
        <h2>Preparing your audiobook</h2>

        <p>
          Connecting to the processing job...
        </p>
      </section>
    );
  }

  return (
    <section>
      <h2>
        {getStageLabel(status.stage)}
      </h2>

      <progress
        value={status.progress}
        max={100}
      />

      <p>
        {status.progress}% complete
      </p>

      {status.message && (
        <p>{status.message}</p>
      )}
    </section>
  );
}

export default BookProcessing;