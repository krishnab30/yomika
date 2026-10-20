
import {
  useEffect,
  useRef,
  useState,
} from "react";

import {
  getChapterAudioUrl,
  type Chapter,
} from "../api/books";

interface AudioPlayerProps {
  bookId: string;
  chapterId: number;
  title: string;
  chapters: Chapter[];
  autoPlay?: boolean;
  onSelectChapter: (
    chapter: Chapter,
    autoPlay?: boolean,
) => void;  onClose: () => void;
  generationActive: boolean;
}

function getPlaybackPositionKey(
  bookId: string,
  chapterId: number,
): string {
  return `audiobook-progress:${bookId}:${chapterId}`;
}

function formatTime(seconds: number): string {
  if (!Number.isFinite(seconds)) {
    return "00:00";
  }

  const totalSeconds = Math.floor(seconds);
  const minutes = Math.floor(totalSeconds / 60);
  const remainingSeconds = totalSeconds % 60;

  return `${minutes
    .toString()
    .padStart(2, "0")}:${remainingSeconds
    .toString()
    .padStart(2, "0")}`;
}

function AudioPlayer({
  bookId,
  chapterId,
  title,
  chapters,
  autoPlay = false,
  generationActive,
  onSelectChapter,
  onClose,
}: AudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [playbackRate, setPlaybackRate] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const [
    waitingAfterEndedChapterId,
    setWaitingAfterEndedChapterId,
  ] = useState<number | null>(null);

  const autoAdvancedFromRef = useRef<number | null>(null);

  const currentIndex = chapters.findIndex(
    (chapter) => chapter.id === chapterId,
  );

  const findPlayableChapter = (direction: -1 | 1): Chapter | null => {
    let index = currentIndex + direction;

    while (index >= 0 && index < chapters.length) {
      const chapter = chapters[index];

      if (chapter.status === "completed") {
        return chapter;
      }

      index += direction;
    }

    return null;
  };

  const previousChapter = findPlayableChapter(-1);
  const nextChapter = findPlayableChapter(1);

  const hasPendingUpcomingChapter =
  currentIndex >= 0 &&
  chapters
    .slice(currentIndex + 1)
    .some(
      (chapter) =>
        chapter.status === "pending" ||
        chapter.status === "processing",
    );

  const audioUrl = getChapterAudioUrl(bookId, chapterId);

  useEffect(() => {
  if (!autoPlay) {
    return;
  }

  const audio = audioRef.current;

  if (!audio) {
    return;
  }

  const startPlayback = async () => {
    try {
      await audio.play();
    } catch (playbackError) {
      const message =
        playbackError instanceof Error
          ? playbackError.message
          : "Unable to play chapter.";

      setError(message);
    }
  };

  void startPlayback();
}, [autoPlay, audioUrl]);

  const togglePlayback = async () => {
    const audio = audioRef.current;

    if (!audio) {
      return;
    }

    try {
      if (audio.paused) {
        await audio.play();
      } else {
        audio.pause();
      }
    } catch (playbackError) {
      const message =
        playbackError instanceof Error
          ? playbackError.message
          : "Unable to play chapter.";

      setError(message);
    }
  };

  const handleSeek = (
    event: React.ChangeEvent<HTMLInputElement>,
  ) => {
    const audio = audioRef.current;

    if (!audio) {
      return;
    }

    const newTime = Number(event.target.value);

    audio.currentTime = newTime;
    setCurrentTime(newTime);
  };

  const handleVolumeChange = (
    event: React.ChangeEvent<HTMLInputElement>,
  ) => {
    const audio = audioRef.current;

    if (!audio) {
      return;
    }

    const newVolume = Number(event.target.value);

    audio.volume = newVolume;
    setVolume(newVolume);
  };

  const handlePlaybackRateChange = (
    event: React.ChangeEvent<HTMLSelectElement>,
  ) => {
    const audio = audioRef.current;

    if (!audio) {
      return;
    }

    const newRate = Number(event.target.value);

    audio.playbackRate = newRate;
    setPlaybackRate(newRate);
  };

  const handleChapterEnded = () => {
    setIsPlaying(false);

    localStorage.removeItem(
      getPlaybackPositionKey(bookId, chapterId),
    );

    if (nextChapter) {
      onSelectChapter(nextChapter, true);
      return;
    }

    if (
      generationActive &&
      hasPendingUpcomingChapter
    ) {
      setWaitingAfterEndedChapterId(chapterId);
    }
  };

  useEffect(() => {
  if (
    waitingAfterEndedChapterId !== chapterId ||
    !nextChapter ||
    autoAdvancedFromRef.current === chapterId
  ) {
    return;
  }

  autoAdvancedFromRef.current = chapterId;

  onSelectChapter(nextChapter, true);
  }, [
  waitingAfterEndedChapterId,
  chapterId,
  nextChapter,
  onSelectChapter,
  ]);

  return (
    <section className="audio-player">
      <div className="audio-player-header">
        <div>
          <p className="audio-player-label">
            Now playing
          </p>

          <h2>{title}</h2>

          <p>
            Chapter {currentIndex + 1} of {chapters.length}
          </p>
        </div>

        <button
          type="button"
          onClick={onClose}
        >
          Close
        </button>
      </div>

      <audio
        ref={audioRef}
        src={audioUrl}
        preload="metadata"
        onLoadedMetadata={(event) => {
          const audio = event.currentTarget;
          const savedPosition = Number(
            localStorage.getItem(
              getPlaybackPositionKey(bookId, chapterId),
            ),
          );

          setDuration(audio.duration);
          setError(null);

          if (
            Number.isFinite(savedPosition) &&
            savedPosition > 0 &&
            savedPosition < audio.duration
           ) {
            audio.currentTime = savedPosition;
            setCurrentTime(savedPosition);
           }
        }}
        onTimeUpdate={(event) => {
          const currentPosition = event.currentTarget.currentTime;

          setCurrentTime(currentPosition);

          localStorage.setItem(
            getPlaybackPositionKey(bookId, chapterId),
            currentPosition.toString(),
          );
        }}
        onPlay={() => {
          setIsPlaying(true);
          setError(null);
        }}
        onPause={() => {
          setIsPlaying(false);
        }}
        onEnded={handleChapterEnded}
        onError={() => {
          setError("The chapter audio could not be loaded.");
        }}
      />

      {error && (
        <p className="error-message">
          {error}
        </p>
      )}

      {waitingAfterEndedChapterId === chapterId &&
        !nextChapter &&
        generationActive && (
          <p
            className="audio-player-waiting"
            role="status"
          >
            This chapter has finished. Waiting for the next
            chapter to finish generating…
          </p>
        )}

      {waitingAfterEndedChapterId === chapterId &&
        !nextChapter &&
        !generationActive && (
          <p
            className="audio-player-waiting"
            role="status"
          >
            No next chapter is ready yet. Continue generation
            to resume the audiobook.
          </p>
        )}

      <div className="audio-player-controls">
        <button
          type="button"
          disabled={!previousChapter}
          onClick={() => {
            if (previousChapter) {
              onSelectChapter(previousChapter);
            }
          }}
        >
          Previous
        </button>

        <button
          type="button"
          onClick={togglePlayback}
        >
          {isPlaying ? "Pause" : "Play"}
        </button>

        <button
          type="button"
          disabled={!nextChapter}
          onClick={() => {
            if (nextChapter) {
              onSelectChapter(nextChapter);
            }
          }}
        >
          Next
        </button>

        <span>{formatTime(currentTime)}</span>

        <input
          type="range"
          min="0"
          max={duration || 0}
          step="0.1"
          value={Math.min(currentTime, duration || 0)}
          onChange={handleSeek}
          disabled={!duration}
          aria-label="Seek chapter"
        />

        <span>{formatTime(duration)}</span>
      </div>

      <div className="audio-player-secondary">
        <label>
          Volume{" "}

          <input
            type="range"
            min="0"
            max="1"
            step="0.01"
            value={volume}
            onChange={handleVolumeChange}
          />
        </label>

        <label>
          Speed{" "}

          <select
            value={playbackRate}
            onChange={handlePlaybackRateChange}
          >
            <option value="0.75">0.75x</option>
            <option value="1">1x</option>
            <option value="1.25">1.25x</option>
            <option value="1.5">1.5x</option>
            <option value="1.75">1.75x</option>
            <option value="2">2x</option>
          </select>
        </label>
      </div>
    </section>
  );
}

export default AudioPlayer;