from fastapi import FastAPI
from backend.app.api.books import router as books_router

app = FastAPI(
    title="Audiobook AI",
    version="0.1.0",
)

app.include_router(books_router)

@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Audiobook AI is running"}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}