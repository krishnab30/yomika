import {
  useCallback,
  useState,
} from "react";

import "./App.css";

import Header from "./components/Header";
import UploadBook from "./components/UploadBook";
import BookProcessing from "./components/BookProcessing";
import BookLibrary from "./components/BookLibrary";
import AudioPlayer from "./components/AudioPlayer";
import {
  continueBook,
  type Book,
  type Chapter,
} from "./api/books";

interface SelectedChapter {
  book: Book;
  chapter: Chapter;
  chapters: Chapter[];
  autoPlay: boolean;
}

function App() {
  const [bookId, setBookId] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [libraryRefreshKey, setLibraryRefreshKey] = useState(0);
  const [activeGenerationIds, setActiveGenerationIds] =
    useState<string[]>([]);
  const [selectedChapter, setSelectedChapter] =
    useState<SelectedChapter | null>(null);

  const handleClosePlayer = () => {
    setSelectedChapter(null);
  };

  const handlePlayChapter = (
    book: Book,
    chapter: Chapter,
    chapters: Chapter[],
    autoPlay = false,
  ) => {
    setSelectedChapter({ book, chapter, chapters, autoPlay });
  };

  const activateGeneration = useCallback(
    (bookId: string) => {
      setActiveGenerationIds((currentIds) => {
        if (currentIds.includes(bookId)) {
          return currentIds;
        }

        return [...currentIds, bookId];
      });
    },
    [],
  );

  const deactivateGeneration = useCallback(
    (bookId: string) => {
      setActiveGenerationIds((currentIds) =>
        currentIds.filter(
          (currentId) => currentId !== bookId,
        ),
      );
    },
    [],
  );

  const handleUploadSuccess = (uploadedBookId: string) => {
    setBookId(uploadedBookId);
    setIsProcessing(true);

    activateGeneration(uploadedBookId);

    setLibraryRefreshKey((current) => current + 1);
  };

  const handleProcessingComplete = () => {
    setIsProcessing(false);

    if (bookId) {
      deactivateGeneration(bookId);
    }

    setLibraryRefreshKey((current) => current + 1);
  };

  const handleContinueGeneration = async (
    book: Book,
  ) => {
    try {
      await continueBook(book.id);

      activateGeneration(book.id);

      setLibraryRefreshKey(
        (current) => current + 1,
      );
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "Unable to continue generation.";

      window.alert(message);
    }
  };

  return (
    <main>
      <Header />

      <p>
        Turn your light novels into audiobooks.
      </p>

      {!isProcessing && (
        <UploadBook
          onUploadSuccess={handleUploadSuccess}
        />
      )}

      {bookId && isProcessing && (
        <BookProcessing
          bookId={bookId}
          onComplete={handleProcessingComplete}
        />
      )}

      <BookLibrary
        refreshKey={libraryRefreshKey}
        activeGenerationIds={activeGenerationIds}
        onGenerationFinished={deactivateGeneration}
        onPlayChapter={handlePlayChapter}
        onContinueGeneration={
          handleContinueGeneration
        }
      />

      {selectedChapter && (
        <AudioPlayer
          key={`${selectedChapter.book.id}-${selectedChapter.chapter.id}`}
          bookId={selectedChapter.book.id}
          chapterId={selectedChapter.chapter.id}
          title={`${selectedChapter.book.title} — ${selectedChapter.chapter.title}`}
          chapters={selectedChapter.chapters}
          onSelectChapter={(chapter, autoPlay = false) => {
            setSelectedChapter({
              ...selectedChapter,
              chapter,
              autoPlay,
            });
          }}
          autoPlay={selectedChapter.autoPlay}
          onClose={handleClosePlayer}
        />
      )}
    </main>
  );
}

export default App;
