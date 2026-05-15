from fastapi import FastAPI

app = FastAPI(title="Unscripted Backend", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, bool]:
    return {"ok": True}
