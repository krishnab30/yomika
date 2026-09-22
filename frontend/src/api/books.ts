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
  created_at: string;
  updated_at: string;
}


export async function uploadBook(
  file: File,
): Promise<BookCreatedResponse> {
  const formData = new FormData();

  formData.append("file", file);

  const response = await fetch("/api/books", {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error(
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