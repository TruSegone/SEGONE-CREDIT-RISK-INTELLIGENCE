# Methodology

Synthetic outcomes are stochastic draws from a logistic latent-risk relationship involving affordability, pricing, delinquencies, employment, loan purpose, term and noise. This creates a controllable demonstration signal, not a representation of a real credit population. Application ID and cohort are not model inputs. The target `defaulted=1` means simulated default.

Data are stratified into development and untouched test partitions; development is split again into train and validation. Imputation, scaling and one-hot encoding are pipeline steps fit on training data. Candidate selection is highest validation ROC-AUC. The selected model is refit on development data and evaluated once on test. Decision metrics use threshold 0.5. No probability calibration is applied. Ranking metrics and probability metrics answer different questions; neither establishes suitability for lending.

Illustrative bands are `<10%`, `10–<25%`, `25–<50%`, and `>=50%`; these are not policy thresholds. SHAP is not yet connected, so local contribution output is explicitly unavailable.
