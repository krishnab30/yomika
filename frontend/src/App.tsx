import {
  useState,
} from "react";

import "./App.css";

import Header from "./components/Header";
import UploadBook from "./components/UploadBook";
import BookProcessing from "./components/BookProcessing";
import BookLibrary from "./components/BookLibrary";
import type { Book } from "./api/books";
import AudioPlayer from "./components/AudioPlayer";

function App() {
  const [bookId, setBookId] =
    useState<string | null>(null);

  const [isProcessing, setIsProcessing] =
    useState(false);

  const [libraryRefreshKey, setLibraryRefreshKey] =
    useState(0);

  const [selectedBook, setSelectedBook] =
  useState<Book | null>(null);

  const handlePlayBook = (
  book: Book,
  ) => {
  setSelectedBook(book);
  };

  const handleClosePlayer = () => {
  setSelectedBook(null);
  };

  const handleUploadSuccess = (
    uploadedBookId: string,
  ) => {
    setBookId(uploadedBookId);
    setIsProcessing(true);

    setLibraryRefreshKey(
      (current) => current + 1,
    );
  };

  const handleProcessingComplete = () => {
    setIsProcessing(false);

    setLibraryRefreshKey(
      (current) => current + 1,
    );
  };

  return (
    <main>
      <Header />

      <p>
        Turn your light novels into audiobooks.
      </p>

      {!isProcessing && (
        <UploadBook
          onUploadSuccess={
            handleUploadSuccess
          }
        />
      )}

      {bookId && isProcessing && (
        <BookProcessing
          bookId={bookId}
          onComplete={
            handleProcessingComplete
          }
        />
      )}

      <BookLibrary
        refreshKey={libraryRefreshKey}
        onPlayBook={handlePlayBook}
      />

      {selectedBook && (
      <AudioPlayer
        key={selectedBook.id}
        bookId={selectedBook.id}
        title={selectedBook.title}
        onClose={handleClosePlayer}
      />
    )}
    </main>
  );
}

export default App;