"""Train candidate classifiers and persist the validation-selected pipeline."""

import json
import os
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from app.ml.data_generator import FEATURES, generate

NUMERIC_FEATURES = [
    feature
    for feature in FEATURES
    if feature not in ("loan_purpose", "employment_category")
]
CATEGORICAL_FEATURES = ["loan_purpose", "employment_category"]
DECISION_THRESHOLD = 0.5


def make_preprocessor() -> ColumnTransformer:
    """Build preprocessing steps that are fitted only inside model pipelines."""
    numeric_pipeline = Pipeline(
        steps=[
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
        ]
    )
    categorical_pipeline = Pipeline(
        steps=[
            ("impute", SimpleImputer(strategy="most_frequent")),
            ("encode", OneHotEncoder(handle_unknown="ignore")),
        ]
    )
    return ColumnTransformer(
        transformers=[
            ("numeric", numeric_pipeline, NUMERIC_FEATURES),
            ("categorical", categorical_pipeline, CATEGORICAL_FEATURES),
        ]
    )


def make_candidates(seed: int) -> dict[str, Any]:
    """Return the available candidate estimators, including XGBoost if present."""
    candidates: dict[str, Any] = {
        "Logistic Regression": LogisticRegression(
            max_iter=1_000,
            class_weight="balanced",
            random_state=seed,
        ),
        "Random Forest": RandomForestClassifier(
            n_estimators=220,
            min_samples_leaf=5,
            class_weight="balanced_subsample",
            n_jobs=-1,
            random_state=seed,
        ),
    }

    try:
        from xgboost import XGBClassifier
    except ImportError:
        print("XGBoost unavailable; training the other configured candidates.")
    else:
        candidates["XGBoost"] = XGBClassifier(
            n_estimators=180,
            max_depth=4,
            learning_rate=0.06,
            subsample=0.85,
            colsample_bytree=0.85,
            eval_metric="logloss",
            n_jobs=4,
            random_state=seed,
        )

    return candidates


def validation_metrics(model: Pipeline, features: pd.DataFrame, target: pd.Series) -> dict:
    """Evaluate ranking and probability quality on the validation split."""
    probability = model.predict_proba(features)[:, 1]
    return {
        "roc_auc": float(roc_auc_score(target, probability)),
        "average_precision": float(average_precision_score(target, probability)),
        "brier_score": float(brier_score_loss(target, probability)),
        "threshold": DECISION_THRESHOLD,
    }


def holdout_metrics(
    model: Pipeline, features: pd.DataFrame, target: pd.Series
) -> dict:
    """Calculate the final report once after choosing the model on validation."""
    probability = model.predict_proba(features)[:, 1]
    predicted_class = probability >= DECISION_THRESHOLD
    return {
        "roc_auc": float(roc_auc_score(target, probability)),
        "average_precision": float(average_precision_score(target, probability)),
        "precision": float(
            precision_score(target, predicted_class, zero_division=0)
        ),
        "recall": float(recall_score(target, predicted_class, zero_division=0)),
        "f1": float(f1_score(target, predicted_class, zero_division=0)),
        "brier_score": float(brier_score_loss(target, probability)),
        "log_loss": float(log_loss(target, probability)),
        "threshold": DECISION_THRESHOLD,
        "confusion_matrix": confusion_matrix(target, predicted_class).tolist(),
    }


def main(n: int = 12_000, seed: int = 42) -> None:
    """Generate/load data, train candidates and save model plus metadata."""
    # In containers this is set to /app; locally, derive the repository root
    # from this module's location so the standard commands need no extra config.
    repository_root = Path(
        os.getenv("SEGONE_PROJECT_ROOT", Path(__file__).resolve().parents[3])
    )
    data_path = repository_root / "data" / "applications.csv"
    artifacts_path = repository_root / "artifacts"
    artifacts_path.mkdir(parents=True, exist_ok=True)

    if data_path.exists():
        frame = pd.read_csv(data_path)
    else:
        frame = generate(n=n, seed=seed)
        data_path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(data_path, index=False)

    features = frame[FEATURES]
    target = frame["defaulted"]

    # Reserve the test set before fitting any preprocessing or choosing a model.
    development_x, test_x, development_y, test_y = train_test_split(
        features,
        target,
        test_size=0.2,
        stratify=target,
        random_state=seed,
    )
    train_x, validation_x, train_y, validation_y = train_test_split(
        development_x,
        development_y,
        test_size=0.2,
        stratify=development_y,
        random_state=seed,
    )

    fitted_candidates: dict[str, Pipeline] = {}
    results: dict[str, dict] = {}
    for name, estimator in make_candidates(seed).items():
        pipeline = Pipeline(
            steps=[
                ("preprocess", make_preprocessor()),
                ("model", estimator),
            ]
        )
        pipeline.fit(train_x, train_y)
        fitted_candidates[name] = pipeline
        results[name] = {
            "validation": validation_metrics(pipeline, validation_x, validation_y)
        }

    # Candidate selection uses validation ROC-AUC only; test metrics do not
    # influence the selected model or its configuration.
    selected_name = max(
        results,
        key=lambda name: results[name]["validation"]["roc_auc"],
    )
    selected_pipeline = fitted_candidates[selected_name]
    selected_pipeline.fit(development_x, development_y)
    results[selected_name]["test_final_holdout"] = holdout_metrics(
        selected_pipeline, test_x, test_y
    )

    import joblib

    joblib.dump(selected_pipeline, artifacts_path / "model.joblib")
    metadata = {
        "selected_model": selected_name,
        "selection_rule": (
            "Highest validation ROC-AUC; fixed threshold 0.5; "
            "test used only for final report."
        ),
        "models": results,
        "feature_schema": FEATURES,
        "model_version": "demo-1.0.0",
    }
    metadata_path = artifacts_path / "evaluation.json"
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
