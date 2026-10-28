"""Generate reproducible synthetic loan applications for the demo."""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

PURPOSES = [
    "debt_consolidation",
    "home_improvement",
    "medical",
    "education",
    "vehicle",
]
EMPLOYMENT = ["salaried", "self_employed", "contract", "part_time"]
FEATURES = [
    "annual_income",
    "loan_amount",
    "interest_rate",
    "loan_term_months",
    "employment_tenure_years",
    "debt_to_income",
    "existing_obligations",
    "previous_delinquencies",
    "credit_history_years",
    "loan_purpose",
    "employment_category",
]


def generate(n: int = 12_000, seed: int = 42) -> pd.DataFrame:
    """Create applications and stochastic outcomes from a latent-risk model.

    The generator is intentionally synthetic. Its relationship is useful for
    exercising ML code, but it does not claim to represent real borrowers.
    """
    if n < 1:
        raise ValueError("n must be greater than zero")

    rng = np.random.default_rng(seed)
    income = np.clip(rng.lognormal(11.0, 0.55, n), 90_000, 2_400_000)
    purpose = rng.choice(PURPOSES, n, p=[0.38, 0.20, 0.13, 0.12, 0.17])
    employment = rng.choice(EMPLOYMENT, n, p=[0.59, 0.16, 0.15, 0.10])
    tenure = np.clip(rng.gamma(2.2, 2.3, n), 0, 35)
    amount = np.clip(
        income * rng.uniform(0.08, 0.62, n) + rng.normal(0, 35_000, n),
        10_000,
        900_000,
    )
    debt_to_income = np.clip(
        rng.beta(2.1, 5.0, n) * 0.85 + 0.08 * (amount / income), 0.01, 0.95
    )
    delinquencies = rng.poisson(0.22 + debt_to_income * 0.55, n).clip(0, 6)
    credit_history = np.clip(rng.gamma(2.8, 3.4, n), 0.2, 35)
    obligations = np.maximum(
        0, income * debt_to_income * rng.uniform(0.15, 0.7, n)
    )
    interest_rate = np.clip(
        7.5
        + debt_to_income * 14
        + delinquencies * 1.8
        + rng.normal(0, 2.0, n),
        4.0,
        32.0,
    )
    term = rng.choice([12, 24, 36, 48, 60], n, p=[0.08, 0.17, 0.39, 0.20, 0.16])

    # Several noisy factors contribute to risk; no single field sets the label.
    log_odds = (
        -3.0
        + 3.0 * debt_to_income
        + 0.035 * (interest_rate - 12)
        + 0.22 * delinquencies
        - 0.07 * tenure
        - 0.035 * credit_history
        + 0.26 * (employment == "part_time")
        + 0.19 * (employment == "contract")
        + 0.15 * (purpose == "medical")
        + 0.08 * (purpose == "debt_consolidation")
        + 0.16 * (term >= 60)
        + rng.normal(0, 0.35, n)
    )
    default_probability = 1 / (1 + np.exp(-log_odds))
    defaulted = rng.binomial(1, default_probability)
    cohorts = pd.period_range("2022-01", "2025-12", freq="M").astype(str)

    frame = pd.DataFrame(
        {
            "application_id": [f"SG-{i:06d}" for i in range(1, n + 1)],
            "cohort": rng.choice(cohorts, n),
            "annual_income": income.round(0),
            "loan_amount": amount.round(0),
            "interest_rate": interest_rate.round(2),
            "loan_term_months": term,
            "employment_tenure_years": tenure.round(1),
            "debt_to_income": debt_to_income.round(3),
            "existing_obligations": obligations.round(0),
            "previous_delinquencies": delinquencies,
            "credit_history_years": credit_history.round(1),
            "loan_purpose": purpose,
            "employment_category": employment,
            "defaulted": defaulted,
        }
    )

    # Missing values exercise the pipeline's imputation steps.
    missing_rates = {"employment_tenure_years": 0.025, "credit_history_years": 0.018}
    for column, missing_rate in missing_rates.items():
        missing_rows = rng.random(n) < missing_rate
        frame.loc[missing_rows, column] = np.nan

    return frame


def main() -> None:
    """Write generated records to a CSV file from the command line."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=12_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", default="data/applications.csv")
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    generate(args.n, args.seed).to_csv(output_path, index=False)
    print(f"Wrote {args.n} synthetic records to {output_path}")


if __name__ == "__main__":
    main()
