# Deployment

For Cloudflare Pages, configure the `frontend` directory, `npm run build`, output `dist`, and `VITE_API_BASE_URL` for the deployed API. Host the backend in a Python-capable container host; install `backend/requirements.txt`, provide the generated `data/applications.csv` and trusted `artifacts/model.joblib` / `evaluation.json`, then run `uvicorn app.main:app --host 0.0.0.0 --port 8000` from `backend`. Set `CORS_ORIGINS` to the exact Pages origin. Generate and train artifacts before deployment. This describes preparation only; no deployment has been executed.
