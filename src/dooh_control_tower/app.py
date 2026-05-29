from fastapi import FastAPI

app = FastAPI(title="DOOH Control Tower", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
