# Story Forge MVP

AI-powered narrative RPG with static frontend and serverless Python backend.

## Structure

- `frontend/`: GitHub Pages static app (`index.html`, `game.html`, Vanilla JS).
- `backend/`: AWS Lambda game API and orchestration.
- `infrastructure/`: AWS SAM template.

## API Routes

- `POST /create-session`
- `POST /start-adventure`
- `POST /next-turn`
- `GET /load-adventure`

## Local notes

Set Lambda environment variables:

- `GEMINI_API_KEY`
- `S3_BUCKET_NAME`
- `IMAGE_BUCKET_NAME`
- `ENVIRONMENT`
