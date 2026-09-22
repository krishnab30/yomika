import {
  useState,
  type ChangeEvent,
  type FormEvent,
} from "react";

import { uploadBook } from "../api/books";

function UploadBook() {
  const [selectedFile, setSelectedFile] =
    useState<File | null>(null);

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
      );

      setMessage(
        `Upload successful: ${result.title}`,
      );
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
    <section>
      <h2>Upload a book</h2>

      <form onSubmit={handleSubmit}>
        <input
          type="file"
          accept=".pdf,application/pdf"
          onChange={handleFileChange}
        />

        <button
          type="submit"
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