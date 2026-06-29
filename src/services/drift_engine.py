import numpy as np
import pandas as pd
from typing import Dict, Any, List
from src.config import settings

class DriftEngine:
    @staticmethod
    def calculate_psi(baseline: np.ndarray, target: np.ndarray, num_bins: int = 10) -> float:
        """Calculates the Population Stability Index (PSI) between baseline and target arrays."""
        # Clean inputs
        base_clean = baseline[~pd.isnull(baseline)]
        targ_clean = target[~pd.isnull(target)]

        if len(base_clean) == 0 or len(targ_clean) == 0:
            return 0.0

        # Create bins based on baseline quantiles
        percentiles = np.linspace(0, 100, num_bins + 1)
        try:
            # Use unique bins to avoid empty intervals
            bins = np.percentile(base_clean, percentiles)
            bins = np.unique(bins)
            if len(bins) < 2:
                # If all values are identical, return 0 or calculate single bin
                return 0.0
        except Exception:
            return 0.0

        # Adjust endpoints slightly to ensure all data is caught
        bins[0] -= 1e-5
        bins[-1] += 1e-5

        # Calculate counts in each bin
        base_counts, _ = np.histogram(base_clean, bins=bins)
        targ_counts, _ = np.histogram(targ_clean, bins=bins)

        # Convert to proportions with smoothing epsilon
        eps = 1e-4
        base_props = (base_counts / len(base_clean)) + eps
        targ_props = (targ_counts / len(targ_clean)) + eps

        # Re-normalize
        base_props /= base_props.sum()
        targ_props /= targ_props.sum()

        # Calculate PSI
        psi = np.sum((targ_props - base_props) * np.log(targ_props / base_props))
        return float(psi)

    @classmethod
    def calculate_drift(cls, df_baseline: pd.DataFrame, df_target: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculates drift metrics between baseline and target DataFrames.
        Returns overall_drift_score and a list of column drift results.
        """
        column_results = []
        scores = []

        for col in df_target.columns:
            if col not in df_baseline.columns:
                continue

            base_col = df_baseline[col]
            targ_col = df_target[col]

            # 1. Numerical Columns
            if np.issubdtype(targ_col.dtype, np.number) and np.issubdtype(base_col.dtype, np.number):
                base_clean = base_col.dropna()
                targ_clean = targ_col.dropna()

                if base_clean.empty or targ_clean.empty:
                    continue

                # A. PSI
                psi = cls.calculate_psi(base_clean.to_numpy(), targ_clean.to_numpy())
                psi_severity = "LOW"
                if psi > settings.PSI_MED_LIMIT:
                    psi_severity = "HIGH"
                elif psi > settings.PSI_LOW_LIMIT:
                    psi_severity = "MEDIUM"

                column_results.append({
                    "column_name": col,
                    "drift_metric": "PSI",
                    "drift_score": psi,
                    "severity": psi_severity
                })
                scores.append(min(psi, 1.0)) # cap score for averaging

                # B. Mean Shift %
                base_mean = base_clean.mean()
                targ_mean = targ_clean.mean()
                mean_shift = abs(targ_mean - base_mean) / (abs(base_mean) if base_mean != 0 else 1.0)
                
                mean_severity = "LOW"
                if mean_shift > settings.MEAN_SHIFT_MED_LIMIT:
                    mean_severity = "HIGH"
                elif mean_shift > settings.MEAN_SHIFT_LOW_LIMIT:
                    mean_severity = "MEDIUM"

                column_results.append({
                    "column_name": col,
                    "drift_metric": "MEAN_SHIFT",
                    "drift_score": float(mean_shift),
                    "severity": mean_severity
                })

                # C. Std Dev Shift %
                base_std = base_clean.std()
                targ_std = targ_clean.std()
                base_std_val = base_std if (pd.notnull(base_std) and base_std > 0) else 1.0
                targ_std_val = targ_std if pd.notnull(targ_std) else 0.0
                std_shift = abs(targ_std_val - base_std_val) / base_std_val

                std_severity = "LOW"
                if std_shift > settings.MEAN_SHIFT_MED_LIMIT:
                    std_severity = "HIGH"
                elif std_shift > settings.MEAN_SHIFT_LOW_LIMIT:
                    std_severity = "MEDIUM"

                column_results.append({
                    "column_name": col,
                    "drift_metric": "STD_SHIFT",
                    "drift_score": float(std_shift),
                    "severity": std_severity
                })

            # 2. Categorical Columns
            else:
                base_clean = base_col.dropna().astype(str)
                targ_clean = targ_col.dropna().astype(str)

                if base_clean.empty or targ_clean.empty:
                    continue

                # A. Distribution Drift (Earth Mover's style / absolute proportion differences)
                base_props = base_clean.value_counts(normalize=True).to_dict()
                targ_props = targ_clean.value_counts(normalize=True).to_dict()

                all_keys = set(base_props.keys()).union(targ_props.keys())
                total_diff = 0.0
                for key in all_keys:
                    diff = abs(targ_props.get(key, 0.0) - base_props.get(key, 0.0))
                    total_diff += diff
                
                # cap/normalize distribution drift between 0 and 1
                dist_drift = min(total_diff / 2.0, 1.0)
                dist_severity = "LOW"
                # using PSI boundaries as proxy for distribution difference
                if dist_drift > settings.PSI_MED_LIMIT:
                    dist_severity = "HIGH"
                elif dist_drift > settings.PSI_LOW_LIMIT:
                    dist_severity = "MEDIUM"

                column_results.append({
                    "column_name": col,
                    "drift_metric": "DIST_DRIFT",
                    "drift_score": dist_drift,
                    "severity": dist_severity
                })
                scores.append(dist_drift)

                # B. Cardinality Drift
                base_card = base_clean.nunique()
                targ_card = targ_clean.nunique()
                card_drift = abs(targ_card - base_card) / (base_card if base_card > 0 else 1)

                card_severity = "LOW"
                if card_drift > settings.CARD_DRIFT_MED_LIMIT:
                    card_severity = "HIGH"
                elif card_drift > settings.CARD_DRIFT_LOW_LIMIT:
                    card_severity = "MEDIUM"

                column_results.append({
                    "column_name": col,
                    "drift_metric": "CARD_DRIFT",
                    "drift_score": float(card_drift),
                    "severity": card_severity
                })

        overall_drift = float(np.mean(scores)) if scores else 0.0

        return {
            "overall_drift_score": overall_drift,
            "results": column_results
        }
