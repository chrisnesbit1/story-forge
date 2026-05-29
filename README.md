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

See `docs/api-contract.yaml` for request and response schemas, including the standard success/error envelope used by every route.

## State synchronization

The backend is the source of truth for `playerState`, including inventory, HP, and gold. The frontend renders the latest state returned by `start-adventure`, `next-turn`, and `load-adventure`.

Each adventure includes an `adventureVersion` that starts at `1` and increments after every successful `next-turn` mutation. The frontend sends `expectedAdventureVersion` with each turn. If another tab has already advanced the adventure, the backend returns `409 VERSION_CONFLICT` with the latest adventure payload. The frontend renders that latest saved state and asks the player to choose an action again instead of applying an optimistic inventory update.

## Image generation

Scene image generation is wired into the backend. On the opening scene, early turns, completion, and larger story beats, the Lambda asks Gemini for a 16:9 scene image, stores the returned image bytes in S3, saves the image key in `currentScene`, and returns a short-lived signed `scene.imageUrl` to the frontend. If image generation or storage fails, the turn still succeeds and the frontend hides the image area until a saved image URL is available.

The image cadence lives in `backend/image_logic.py`. The model defaults to `gemini-2.5-flash-image` and can be changed with `GEMINI_IMAGE_MODEL`.

## Production controls

The API can run open for local demos, but production deployments should enable the optional shared API key and/or rate limit:

- `STORY_FORGE_API_KEY`: when set, requests must include the value as `X-Api-Key` or `Authorization: Bearer <key>`.
- `RATE_LIMIT_PER_MINUTE`: when greater than `0`, the Lambda applies a best-effort per-client in-memory request limit for each warm execution environment.

## Local notes

Set Lambda environment variables:

- `GEMINI_API_KEY`
- `GEMINI_IMAGE_MODEL` (optional; defaults to `gemini-2.5-flash-image`)
- `S3_BUCKET_NAME`
- `IMAGE_BUCKET_NAME`
- `ENVIRONMENT`
- `STORY_FORGE_API_KEY` (optional)
- `RATE_LIMIT_PER_MINUTE` (optional; `0` disables rate limiting)

For static frontend deployments that use `STORY_FORGE_API_KEY`, expose the matching key as `window.STORY_FORGE_API_KEY` before loading `frontend/api.js`.

## Deployment

Install and configure the AWS SAM CLI with credentials for the target AWS account, then deploy from the repository root:

```sh
cd infrastructure
sam build
sam deploy --guided \
  --parameter-overrides \
  GeminiApiKey=<your-gemini-api-key> \
  StoryForgeApiKey=<optional-shared-api-key> \
  RateLimitPerMinute=0 \
  GeminiImageModel=gemini-2.5-flash-image
```

On later deploys, reuse the generated `samconfig.toml`:

```sh
cd infrastructure
sam build
sam deploy
```

Required Lambda environment variables are wired by `infrastructure/template.yaml`: `S3_BUCKET_NAME`, `IMAGE_BUCKET_NAME`, `GEMINI_API_KEY`, `GEMINI_IMAGE_MODEL`, `STORY_FORGE_API_KEY`, and `RATE_LIMIT_PER_MINUTE`. `S3_BUCKET_NAME` and `GEMINI_API_KEY` are validated at Lambda cold start; missing values fail startup with a clear log entry.
