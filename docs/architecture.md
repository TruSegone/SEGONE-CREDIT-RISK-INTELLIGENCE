# Architecture

The Vite frontend makes typed JSON/CSV HTTP requests to a single FastAPI service. The service reads a generated local synthetic dataset and loads one trusted Joblib pipeline trained by the repository scripts. No external account, database or financial integration is required.
