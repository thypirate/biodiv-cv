"""Dev entrypoint: `uv run main.py` (or `uv run uvicorn app.main:app --reload`)."""

import uvicorn


def main() -> None:
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    main()
