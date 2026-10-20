
export interface BookCreatedResponse {
  book_id: string;
  title: string;
  status: string;
}

export interface BookStatusResponse {
  book_id: string;
  status: string;
  stage: string;
  progress: number;
  message: string;
  updated_at: string;
}

export interface Book {
  id: string;
  title: string;
  original_filename: string;
  status: string;
  stage: string;
  progress: number;
  message: string;
  chapter_count: number;
  completed_chapter_count: number;
  pending_chapter_count: number;
  created_at: string;
  updated_at: string;
}

export interface Chapter {
  id: number;
  chapter_number: number | null;
  title: string;
  filename: string | null;
  duration_seconds: number | null;
  status: string;
}

export type GenerationScope =
  | "first_chapter"
  | "all_chapters";


export async function uploadBook(
  file: File,
  voice: string = "af_heart",
  generationScope: GenerationScope = "first_chapter",
): Promise<BookCreatedResponse> {
  const formData = new FormData();

  formData.append("file", file);
  formData.append("voice", voice);
  formData.append("generation_scope", generationScope);

  const response = await fetch("/api/books", {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);

    throw new Error(
      errorBody?.detail ??
        `Upload failed: ${response.status}`,
    );
  }

  return response.json();
}



export async function getBookStatus(
  bookId: string,
): Promise<BookStatusResponse> {
  const response = await fetch(
    `/api/books/${bookId}/status`,
  );

  if (!response.ok) {
    throw new Error(
      `Failed to fetch book status: ${response.status}`,
    );
  }

  return response.json();
}

export async function getBooks(): Promise<Book[]> {
  const response = await fetch("/api/books");

  if (!response.ok) {
    throw new Error(
      `Failed to fetch books: ${response.status}`,
    );
  }

  return response.json();
}

export async function getChapters(
  bookId: string,
): Promise<Chapter[]> {
  const response = await fetch(
    `/api/books/${bookId}/chapters`,
  );

  if (!response.ok) {
    throw new Error(
      `Failed to fetch chapters: ${response.status}`,
    );
  }

  return response.json();
}

export function getChapterAudioUrl(
  bookId: string,
  chapterId: number,
): string {
  return `/api/books/${bookId}/chapters/${chapterId}/audio`;
}

export function getVoicePreviewUrl(
  voice: string,
): string {
  return `/api/books/voice-previews/${voice}`;
}

export function getChapterArchiveUrl(
  bookId: string,
): string {
  return `/api/books/${bookId}/download-chapters`;
}

// Kept temporarily for the existing player.
// We'll remove this when the frontend switches to chapter playback.
export function getBookAudioUrl(
  bookId: string,
): string {
  return `/api/books/${bookId}/audio`;
}

export async function continueBook(
  bookId: string,
): Promise<BookCreatedResponse> {
  const response = await fetch(
    `/api/books/${bookId}/continue`,
    {
      method: "POST",
    },
  );

  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);

    throw new Error(
      errorBody?.detail ??
        "Unable to continue audiobook generation.",
    );
  }

  return response.json();
}


export async function deleteBook(
  bookId: string,
): Promise<{
  book_id: string;
  message: string;
  files_removed: boolean;
}> {
  const response = await fetch(
    `/api/books/${bookId}`,
    {
      method: "DELETE",
    },
  );

  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);

    throw new Error(
      errorBody?.detail ?? "Unable to delete book.",
    );
  }

  return response.json();
}
