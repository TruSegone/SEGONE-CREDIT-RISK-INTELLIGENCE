# Public preview deployment

The app needs a deployed frontend and a deployed API. `render.yaml` defines the API service; its Docker image installs dependencies and trains the deterministic synthetic model during the image build. Cloudflare Pages builds the React frontend from this repository.

## 1. Deploy the API on Render

1. Sign in to Render and create a Blueprint from `TruSegone/SEGONE-CREDIT-RISK-INTELLIGENCE`.
2. Approve the `segone-credit-risk-api` service from `render.yaml`.
3. When prompted for `CORS_ORIGINS`, enter the exact production Pages origin, for example `https://segone-credit-risk-intelligence.pages.dev` (use the actual project name assigned by Pages).
4. Wait for the Docker build and health check. The service URL will look like `https://segone-credit-risk-api.onrender.com`.
5. Verify `/health`, `/api/v1/health/ready`, and `/api/v1/portfolio/summary` on that service URL.

Render's free web service may sleep while idle, so the first viewer request can take longer while the service wakes.

## 2. Deploy the frontend on Cloudflare Pages

1. Create a Pages project connected to the same GitHub repository.
2. Set the root directory to `frontend`, build command to `npm run build`, and output directory to `dist`.
3. Add the build environment variable `VITE_API_BASE_URL` with the Render API service URL, without a trailing slash.
4. Deploy. Open the Pages URL and check that the overview loads real API metrics and that the applicant assessment can submit.

The Pages origin must match the API's `CORS_ORIGINS` value exactly. If the Pages project name or custom domain changes, update `CORS_ORIGINS` on Render and redeploy the API. Preview-branch URLs are not included by default; add only trusted preview origins if they are needed.

## Local Docker

From the repository root, run `docker compose up --build`. Compose uses the local host-generated dataset and model folders; the Render API image trains its artifacts during its own build. No deployment has been performed by this repository configuration alone.
