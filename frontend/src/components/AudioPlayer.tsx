import {
//   useEffect,
  useRef,
  useState,
} from "react";

import { getBookAudioUrl } from "../api/books";

interface AudioPlayerProps {
  bookId: string;
  title: string;
  onClose: () => void;
}

function formatTime(seconds: number): string {
  if (!Number.isFinite(seconds)) {
    return "00:00";
  }

  const totalSeconds = Math.floor(
    seconds,
  );

  const minutes = Math.floor(
    totalSeconds / 60,
  );

  const remainingSeconds =
    totalSeconds % 60;

  return `${minutes
    .toString()
    .padStart(2, "0")}:${remainingSeconds
    .toString()
    .padStart(2, "0")}`;
}

function AudioPlayer({
  bookId,
  title,
  onClose,
}: AudioPlayerProps) {
  const audioRef =
    useRef<HTMLAudioElement | null>(null);

  const [isPlaying, setIsPlaying] =
    useState(false);

  const [currentTime, setCurrentTime] =
    useState(0);

  const [duration, setDuration] =
    useState(0);

  const [volume, setVolume] =
    useState(1);

  const [playbackRate, setPlaybackRate] =
    useState(1);

  const [error, setError] =
    useState<string | null>(null);

  const audioUrl =
    getBookAudioUrl(bookId);

//   useEffect(() => {
//     setIsPlaying(false);
//     setCurrentTime(0);
//     setDuration(0);
//     setError(null);

//     const audio = audioRef.current;

//     if (!audio) {
//       return;
//     }

//     audio.load();
//   }, [bookId]);

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
          : "Unable to play audiobook.";

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

    const newTime = Number(
      event.target.value,
    );

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

    const newVolume = Number(
      event.target.value,
    );

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

    const newRate = Number(
      event.target.value,
    );

    audio.playbackRate = newRate;
    setPlaybackRate(newRate);
  };

  return (
    <section className="audio-player">
      <div className="audio-player-header">
        <div>
          <p className="audio-player-label">
            Now playing
          </p>

          <h2>{title}</h2>
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
          setDuration(
            event.currentTarget.duration,
          );
        }}
        onTimeUpdate={(event) => {
          setCurrentTime(
            event.currentTarget.currentTime,
          );
        }}
        onPlay={() => {
          setIsPlaying(true);
        }}
        onPause={() => {
          setIsPlaying(false);
        }}
        onEnded={() => {
          setIsPlaying(false);
        }}
        onError={() => {
          setError(
            "The audiobook could not be loaded.",
          );
        }}
      />

      {error && (
        <p className="error-message">
          {error}
        </p>
      )}

      <div className="audio-player-controls">
        <button
          type="button"
          onClick={togglePlayback}
        >
          {isPlaying ? "Pause" : "Play"}
        </button>

        <span>
          {formatTime(currentTime)}
        </span>

        <input
          type="range"
          min="0"
          max={duration || 0}
          step="0.1"
          value={Math.min(
            currentTime,
            duration || 0,
          )}
          onChange={handleSeek}
          disabled={!duration}
          aria-label="Seek audiobook"
        />

        <span>
          {formatTime(duration)}
        </span>
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
            onChange={
              handlePlaybackRateChange
            }
          >
            <option value="0.75">
              0.75x
            </option>

            <option value="1">
              1x
            </option>

            <option value="1.25">
              1.25x
            </option>

            <option value="1.5">
              1.5x
            </option>

            <option value="1.75">
              1.75x
            </option>

            <option value="2">
              2x
            </option>
          </select>
        </label>
      </div>
    </section>
  );
}

export default AudioPlayer;