export interface BookCreatedResponse {
  book_id: string;
  title: string;
  status: string;
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