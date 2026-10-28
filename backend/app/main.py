"""FastAPI application for synthetic credit-risk analytics and inference."""

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, model_validator

from app.ml.data_generator import EMPLOYMENT, FEATURES, PURPOSES, generate

REPOSITORY_ROOT = Path(
    os.getenv("SEGONE_PROJECT_ROOT", Path(__file__).resolve().parents[2])
)
ARTIFACTS_PATH = REPOSITORY_ROOT / "artifacts"
DATA_PATH = REPOSITORY_ROOT / "data" / "applications.csv"
DISCLAIMER = (
    "Educational synthetic-data demonstration only; not for lending decisions."
)
RISK_BANDS = [
    {"name": "Lower illustrative risk", "range": "<10%"},
    {"name": "Moderate illustrative risk", "range": "10% to <25%"},
    {"name": "Elevated illustrative risk", "range": "25% to <50%"},
    {"name": "Higher illustrative risk", "range": ">=50%"},
]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("segone")
app = FastAPI(title="SEGONE Credit Risk Intelligence API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv(
        "CORS_ORIGINS", "http://localhost:5173"
    ).split(","),
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# The model is loaded once per process and reused for subsequent requests.
_model = None


class Applicant(BaseModel):
    """Canonical model input schema shared with the training pipeline."""

    annual_income: float = Field(gt=0, le=100_000_000)
    loan_amount: float = Field(gt=0, le=10_000_000)
    interest_rate: float = Field(ge=0, le=100)
    loan_term_months: int = Field(ge=1, le=480)
    employment_tenure_years: float | None = Field(default=None, ge=0, le=80)
    debt_to_income: float = Field(ge=0, le=1)
    existing_obligations: float = Field(ge=0)
    previous_delinquencies: int = Field(ge=0, le=50)
    credit_history_years: float | None = Field(default=None, ge=0, le=100)
    loan_purpose: str
    employment_category: str

    @model_validator(mode="after")
    def validate_categories(self) -> "Applicant":
        """Reject categories the persisted model was not trained to accept."""
        if self.loan_purpose not in PURPOSES:
            raise ValueError("Unsupported loan purpose")
        if self.employment_category not in EMPLOYMENT:
            raise ValueError("Unsupported employment category")
        return self


class Prediction(BaseModel):
    """Public response schema for an individual model estimate."""

    assessment_id: str
    model_version: str
    probability_default: float
    risk_band: str
    assessed_at: str
    explanation_available: bool
    disclaimer: str


@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    """Attach a request ID to each response without logging applicant data."""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


def get_data() -> pd.DataFrame:
    """Load the local generated dataset, or create an in-memory demo dataset."""
    if DATA_PATH.exists():
        return pd.read_csv(DATA_PATH)
    return generate(12_000)


def risk_band(probability: float) -> str:
    """Map probability to centralized illustrative ranges."""
    if probability < 0.10:
        return "Lower illustrative risk"
    if probability < 0.25:
        return "Moderate illustrative risk"
    if probability < 0.50:
        return "Elevated illustrative risk"
    return "Higher illustrative risk"


def load_model():
    """Load only the trusted local artifact created by the training script."""
    global _model
    if _model is None:
        try:
            import joblib

            _model = joblib.load(ARTIFACTS_PATH / "model.joblib")
        except Exception as error:
            logger.exception("Could not load the trained model artifact")
            raise HTTPException(
                status_code=503,
                detail="Model unavailable; run the training command first",
            ) from error
    return _model


def load_evaluation_metadata() -> dict:
    """Read evaluation output when available without exposing host paths."""
    metadata_path = ARTIFACTS_PATH / "evaluation.json"
    if not metadata_path.exists():
        return {}
    return json.loads(metadata_path.read_text(encoding="utf-8"))


def filter_records(
    purposes: list[str] | None,
    cohorts: list[str] | None,
    search: str | None = None,
) -> pd.DataFrame:
    """Apply the supported dataset filters before pagination or aggregation."""
    frame = get_data()
    if purposes:
        frame = frame[frame["loan_purpose"].isin(purposes)]
    if cohorts:
        frame = frame[frame["cohort"].isin(cohorts)]
    if search:
        frame = frame[
            frame["application_id"].str.contains(search, case=False, regex=False)
        ]
    return frame


@app.get("/health")
def health() -> dict:
    """Report that the API process is responding."""
    return {"status": "ok"}


@app.get("/api/v1/health/ready")
def readiness() -> dict:
    """Report whether a trained model artifact is present."""
    model_available = (ARTIFACTS_PATH / "model.joblib").exists()
    return {"ready": model_available, "model_available": model_available}


@app.get("/api/v1/metadata")
def metadata() -> dict:
    """Describe the selected model, feature schema, dataset and demo bands."""
    evaluation = load_evaluation_metadata()
    return {
        "model_version": evaluation.get("model_version", "untrained"),
        "feature_schema": FEATURES,
        "dataset_rows": len(get_data()),
        "selected_model": evaluation.get("selected_model"),
        "risk_bands": RISK_BANDS,
    }


@app.get("/api/v1/portfolio/summary")
def portfolio_summary(
    purpose: list[str] | None = Query(default=None),
    cohort: list[str] | None = Query(default=None),
    loan_min: float | None = None,
    loan_max: float | None = None,
) -> dict:
    """Return outcomes and model probabilities for the filtered population."""
    frame = filter_records(purpose, cohort)
    if loan_min is not None:
        frame = frame[frame["loan_amount"] >= loan_min]
    if loan_max is not None:
        frame = frame[frame["loan_amount"] <= loan_max]

    probabilities = (
        load_model().predict_proba(frame[FEATURES])[:, 1] if not frame.empty else []
    )
    return {
        "applications": len(frame),
        "known_outcomes": int(frame["defaulted"].notna().sum()),
        "simulated_defaults": int(frame["defaulted"].sum()),
        "observed_default_rate": (
            float(frame["defaulted"].mean()) if not frame.empty else None
        ),
        "average_predicted_probability": (
            float(probabilities.mean()) if len(probabilities) else None
        ),
        "high_risk_count": (
            int((probabilities >= 0.50).sum()) if len(probabilities) else 0
        ),
    }


@app.get("/api/v1/portfolio/records")
def portfolio_records(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    search: str | None = None,
    loan_min: float | None = None,
    loan_max: float | None = None,
    purpose: list[str] | None = Query(default=None),
    cohort: list[str] | None = Query(default=None),
    sort_by: str = "loan_amount",
    descending: bool = True,
) -> dict:
    """Return a validated, sorted page of synthetic application records."""
    frame = filter_records(purpose, cohort, search)
    probabilities = load_model().predict_proba(frame[FEATURES])[:, 1]
    frame = frame.copy()
    frame["probability_default"] = probabilities
    frame["risk_band"] = [risk_band(value) for value in probabilities]

    if loan_min is not None:
        frame = frame[frame["loan_amount"] >= loan_min]
    if loan_max is not None:
        frame = frame[frame["loan_amount"] <= loan_max]
    if sort_by not in frame.columns:
        raise HTTPException(status_code=400, detail="Unsupported sort field")

    total = len(frame)
    start = (page - 1) * page_size
    page_frame = frame.sort_values(sort_by, ascending=not descending).iloc[
        start : start + page_size
    ]
    # Convert missing values to JSON null rather than serializing NaN.
    records = page_frame.astype(object).where(pd.notna(page_frame), None)
    return {
        "items": records.to_dict(orient="records"),
        "page": page,
        "page_size": page_size,
        "total": total,
    }


@app.get("/api/v1/portfolio/distributions")
def portfolio_distributions() -> dict:
    """Aggregate risk bands, purposes, and cohorts for portfolio charts."""
    frame = get_data()
    probabilities = load_model().predict_proba(frame[FEATURES])[:, 1]
    frame = frame.copy()
    frame["probability_default"] = probabilities
    frame["risk_band"] = [risk_band(value) for value in probabilities]

    by_purpose = (
        frame.groupby("loan_purpose")
        .agg(
            applications=("defaulted", "size"),
            observed_default_rate=("defaulted", "mean"),
            average_predicted_probability=("probability_default", "mean"),
        )
        .reset_index()
    )
    by_cohort = (
        frame.groupby("cohort")
        .agg(
            applications=("defaulted", "size"),
            observed_default_rate=("defaulted", "mean"),
            average_predicted_probability=("probability_default", "mean"),
        )
        .reset_index()
    )
    risk_counts = (
        frame.groupby("risk_band").size().rename("count").reset_index()
    )
    return {
        "risk_bands": risk_counts.to_dict(orient="records"),
        "by_purpose": by_purpose.to_dict(orient="records"),
        "by_cohort": by_cohort.to_dict(orient="records"),
    }


@app.get("/api/v1/models/compare")
def model_comparison() -> dict:
    """Return persisted candidate evaluation metadata."""
    return load_evaluation_metadata() or {"status": "untrained", "models": {}}


@app.get("/api/v1/data/profile")
def data_profile() -> dict:
    """Expose summary statistics for the controlled synthetic dataset only."""
    frame = get_data()
    feature_profile = [
        {
            "name": column,
            "dtype": str(frame[column].dtype),
            "missing_pct": round(float(frame[column].isna().mean() * 100), 2),
            "unique": int(frame[column].nunique()),
        }
        for column in frame.columns
    ]
    return {
        "rows": len(frame),
        "columns": len(frame.columns),
        "target_balance": frame["defaulted"].value_counts(normalize=True).to_dict(),
        "features": feature_profile,
        "summary": frame.describe(include="all").fillna("").to_dict(),
    }


@app.post("/api/v1/predictions", response_model=Prediction)
def create_prediction(applicant: Applicant) -> Prediction:
    """Score one request in memory; applicant inputs are not persisted."""
    model_input = pd.DataFrame(
        [{feature: getattr(applicant, feature) for feature in FEATURES}]
    )
    probability = float(load_model().predict_proba(model_input)[0, 1])
    evaluation = load_evaluation_metadata()
    return Prediction(
        assessment_id=str(uuid.uuid4()),
        model_version=evaluation.get("model_version", "demo-1.0.0"),
        probability_default=probability,
        risk_band=risk_band(probability),
        assessed_at=datetime.now(timezone.utc).isoformat(),
        explanation_available=False,
        disclaimer=DISCLAIMER,
    )


@app.post("/api/v1/explanations")
def create_explanation(_applicant: Applicant) -> None:
    """Return a clear unavailable state until a supported SHAP method exists."""
    raise HTTPException(
        status_code=503,
        detail="Local explanation unavailable: SHAP support is not configured.",
    )


@app.get("/api/v1/portfolio/export")
def export_portfolio(
    purpose: list[str] | None = Query(default=None),
    cohort: list[str] | None = Query(default=None),
) -> Response:
    """Export filtered synthetic records as a CSV attachment."""
    frame = filter_records(purpose, cohort)
    return Response(
        content=frame.to_csv(index=False),
        media_type="text/csv",
        headers={
            "Content-Disposition": (
                "attachment; filename=segone-synthetic-portfolio.csv"
            )
        },
    )
