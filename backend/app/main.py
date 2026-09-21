from fastapi import FastAPI

app = FastAPI(
    title="Audiobook AI",
    version="0.1.0",
)


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Audiobook AI is running"}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}