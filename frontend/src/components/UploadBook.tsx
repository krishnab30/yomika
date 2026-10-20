import {
  useRef,
  useState,
  type ChangeEvent,
  type FormEvent,
} from "react";

import { getVoicePreviewUrl, uploadBook , type GenerationScope, } from "../api/books";

interface UploadBookProps {
  onUploadSuccess: (bookId: string) => void;
}

function UploadBook({ onUploadSuccess }: UploadBookProps) {
  const [selectedFile, setSelectedFile] =
    useState<File | null>(null);

  const [selectedVoice, setSelectedVoice] =
    useState("af_heart");

  const [generationScope, setGenerationScope] =
    useState<GenerationScope>("first_chapter");
  
  const previewAudioRef = 
    useRef<HTMLAudioElement | null>(null);

  const [previewMessage, setPreviewMessage] = 
    useState("");

  const [isUploading, setIsUploading] =
    useState(false);

  const [message, setMessage] =
    useState("");

  const handleFileChange = (
    event: ChangeEvent<HTMLInputElement>,
  ) => {
    const file = event.target.files?.[0] ?? null;

    setSelectedFile(file);
    setMessage("");
  };

  const handleVoiceChange = (
  event: ChangeEvent<HTMLSelectElement>,
) => {
  const audio = previewAudioRef.current;

  if (audio) {
    audio.pause();
    audio.currentTime = 0;
  }

  setSelectedVoice(event.target.value);
  setPreviewMessage("");
};

  const handlePreviewVoice = async () => {
    const audio = previewAudioRef.current;

    if (!audio) {
      return;
    }

    setPreviewMessage("");

    try {
      audio.currentTime = 0;
      await audio.play();
    } catch {
      setPreviewMessage(
        "Unable to play the preview. Check that the backend is running and the preview file is available.",
      );
    }
  };

  const handleSubmit = async (
    event: FormEvent<HTMLFormElement>,
  ) => {
    event.preventDefault();

    if (!selectedFile) {
      setMessage("Please select a PDF first.");
      return;
    }

    setIsUploading(true);
    setMessage("");

    try {
      const result = await uploadBook(
        selectedFile,
        selectedVoice,
        generationScope,
      );

      setMessage(
        `Upload successful: ${result.title}`,
      );

      onUploadSuccess(result.book_id);
    } catch (error) {
      const errorMessage =
        error instanceof Error
          ? error.message
          : "Upload failed.";

      setMessage(errorMessage);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <section className="upload-book-section">
      <h2>Upload a book</h2>

      <form onSubmit={handleSubmit}>
        <input
          type="file"
          accept=".pdf,application/pdf"
          onChange={handleFileChange}
        />

        <label htmlFor="voice-select">
          Narration voice
        </label>

        <select
          id="voice-select"
          value={selectedVoice}
          onChange={handleVoiceChange}
          disabled={isUploading}
        >
          <option value="af_heart">
            Heart — Female
          </option>
          <option value="af_bella">
            Bella — Female
          </option>
          <option value="af_nicole">
            Nicole — Female
          </option>
          <option value="af_sarah">
            Sarah — Female
          </option>
          <option value="am_michael">
            Michael — Male
          </option>
          <option value="am_fenrir">
            Fenrir — Male
          </option>
        </select>

        <div className="voice-preview-controls">
        <button
          type="button"
          className="button-secondary"
          onClick={() => void handlePreviewVoice()}
          disabled={isUploading}
        >
          Preview voice
        </button>

        <audio
          key={selectedVoice}
          ref={previewAudioRef}
          src={getVoicePreviewUrl(selectedVoice)}
          controls
          preload="none"
          aria-label={`Preview of ${selectedVoice}`}
        />
      </div>


        <label htmlFor="generation-scope">
          Generation scope
        </label>

        <select
          id="generation-scope"
          value={generationScope}
          onChange={(event) =>
            setGenerationScope(
              event.target.value as GenerationScope,
            )
          }
          disabled={isUploading}
        >
          <option value="first_chapter">
            First chapter only — quick test
          </option>
          <option value="all_chapters">
            Entire book — generate all chapters
          </option>
        </select>

        <p className="generation-scope-help">
          {generationScope === "first_chapter"
            ? "Generate the first chapter now. Generate the remaining chapters later using Continue generation."
            : "Generate all chapters immediately. This may take a while for longer books."}
        </p>


      {previewMessage && (
        <p role="status" className="error-message">
          {previewMessage}
        </p>
      )}

        <button
          type="submit"
          className="upload-submit-button"
          disabled={
            isUploading || !selectedFile
          }
        >
          {isUploading
            ? "Uploading..."
            : "Upload PDF"}
        </button>
      </form>

      {selectedFile && (
        <p>
          Selected: {selectedFile.name}
        </p>
      )}

      {message && <p>{message}</p>}
    </section>
  );
}

export default UploadBook;