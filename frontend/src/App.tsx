import {
  useState,
} from "react";

import "./App.css";

import Header from "./components/Header";
import UploadBook from "./components/UploadBook";
import BookProcessing from "./components/BookProcessing";

function App() {
  const [bookId, setBookId] =
    useState<string | null>(null);

  const [isProcessing, setIsProcessing] =
    useState(false);

  const handleUploadSuccess = (
    uploadedBookId: string,
  ) => {
    setBookId(uploadedBookId);
    setIsProcessing(true);
  };

  const handleProcessingComplete = () => {
    setIsProcessing(false);
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
    </main>
  );
}

export default App;