"""Explicit pre-test cohort and feature contracts for the manuscript reanalysis.

Unlike the exploratory processor, this module never imputes an unrecorded test
as negative or an unrecorded history as absent. Numeric quality failures become
missing values, not silent patient exclusions. All transformations are fixed
clinical definitions; no quantile or outcome-dependent cut-point is learned.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import numpy as np
import pandas as pd

TESTED = ("Buscada positivo", "Buscada negativo")

@dataclass(frozen=True)
class Outcome:
    """Registry field, display name, positive label, and reporting priority."""
    column: str
    label: str
    positive: str = "Sí"
    priority: str = "exploratory"

OUTCOMES = (
    Outcome("ana_dura", "Composite thrombophilia", "Buscada positivo", "composite"),
    Outcome("var156", "Factor V Leiden", priority="primary"),
    Outcome("var157", "Prothrombin G20210A", priority="primary"),
    Outcome("var161", "Registry-coded APS"),
    Outcome("var155", "Protein S deficiency"),
    Outcome("var154", "Protein C deficiency"),
    Outcome("var158", "Antithrombin deficiency"),
    Outcome("andujak2", "JAK2 mutation", priority="descriptive"),
)

# Explicit allowlist: adding columns to the registry cannot silently add predictors.
CATEGORICAL = {
    "sexo": "Sex", "raza": "Recorded ethnicity", "ant_inf": "Prior myocardial ischemia",
    "ant_isq": "Prior cerebral ischemia", "ant_clau": "Peripheral arterial disease",
    "fum_act": "Current smoking", "diabetes": "Diabetes", "hip_art": "Hypertension",
    "insf_car": "Heart failure", "fibr_aur": "Atrial fibrillation",
    "trat_est": "Statin treatment",  # Confirmed in the supplied variable dictionary.
    "e_con_pp": "Chronic lung disease", "e_con_cu": "Ulcerative colitis",
    "e_con_ec": "Crohn disease", "e_con_lu": "Known lupus",
    "e_con_be": "Behcet disease", "e_con_at": "Temporal arteritis",
    "e_con_va": "Other vasculitis", "e_con_ar": "Rheumatoid arthritis",
    "e_con_ea": "Ankylosing spondylitis", "e_con_pr": "Polymyalgia rheumatica",
    "e_con_ro": "Rendu-Osler disease", "e_con_av": "Vena cava agenesis",
    "e_con_sm": "May-Thurner syndrome", "sin_tvp_": "Index VTE presentation",
    "var171": "Syncope", "tv_l_esu": "Upper-extremity thrombosis",
    "tvp_orig": "Upper-extremity catheter relationship", "tv_l_ein": "Lower-extremity thrombosis",
    "tvp_prox": "DVT proximal/distal location", "tv_l_svc": "Cerebral sinus thrombosis",
    "tv_l_vre": "Retinal vein thrombosis", "tv_l_vrn": "Renal vein thrombosis",
    "tv_l_vca": "Vena cava thrombosis", "tv_l_yug": "Jugular vein thrombosis",
    "tv_l_ova": "Ovarian vein thrombosis", "tv_l_sup": "Suprahepatic vein thrombosis",
    "tv_l_pul": "Pulmonary vein thrombosis", "tv_l_ove": "Other vein thrombosis",
    "fr_cance": "Active cancer", "fr_cirug": "Recent surgery",
    "fr_inmov": "Recent immobilization", "fr_tvp_a": "Prior VTE",
    "fr_antfa": "Family history of VTE", "fr_tvs_a": "Prior superficial thrombosis",
    "fr_viaje": "Recent prolonged travel", "fr_estro": "Recent hormone exposure",
    "fr_embar": "Pregnancy", "fr_varic": "Varicose veins", "fr_antec": "Recent delivery",
    "ana_dime": "Recorded categorical D-dimer", "ana_crea": "Recorded creatinine category",
    "ana_trop": "Recorded troponin category",
}
NUMERIC = {
    "edad": (0, 120, [-np.inf, 50, 70, np.inf], ["<50", "50–69", "≥70"], "Age (years)"),
    "peso": (29, 300, [-np.inf, 50, 100.0000001, np.inf], ["<50", "50–100", ">100"], "Weight (kg)"),
    "tension_": (35, 300, [-np.inf, 100, np.inf], ["<100", "≥100"], "Systolic BP (mmHg)"),
    "ana_hemo": (4, 20, [-np.inf, 12, np.inf], ["<12", "≥12"], "Hemoglobin (g/dL)"),
    "ana_plaq": (10, 1500, [-np.inf, 144, 400.0000001, np.inf], ["<144", "144–400", ">400"], "Platelets (10^9/L)"),
    "ana_leuc": (2, 40, [-np.inf, 4, 11.0000001, np.inf], ["<4", "4–11", ">11"], "Leukocytes (10^9/L)"),
    "ana_neu": (.4, 30, [-np.inf, 1.5, 8.0000001, np.inf], ["<1.5", "1.5–8", ">8"], "Neutrophils (10^9/L)"),
    "protcrea": (0, 200, [-np.inf, .5, np.inf], ["<0.5", "≥0.5"], "C-reactive protein (mg/dL)"),
}
LABELS = {**CATEGORICAL, **{k: v[-1] for k, v in NUMERIC.items()},
          "female_under45": "Female and age <45", "splanchnic": "Splanchnic thrombosis"}


def load_registry(path: Path) -> pd.DataFrame:
    """Read raw Parquet and reject duplicate/missing IDs and absent cohort fields."""
    data = pd.read_parquet(path)
    required = {"id_pacie", "ana_dura", "fecha_di", "ana_port", "e_con_af"}
    if not required.issubset(data):
        raise ValueError(f"Raw registry is required; missing columns: {sorted(required - set(data))}")
    if data.id_pacie.isna().any() or data.id_pacie.duplicated().any():
        raise ValueError("One unique, nonmissing id_pacie per patient is required.")
    return data


def text_values(series: pd.Series) -> pd.Series:
    """Normalize recorded category spellings without filling absent observations."""
    return (series.astype("string").str.strip()
            .replace({"": pd.NA, "Missing": pd.NA, "missing": pd.NA,
                      "Sí": "Yes", "Si": "Yes", "Hombre": "Male", "Mujer": "Female",
                      "TVP/EP": "PE+DVT", "EP+TVP": "PE+DVT", "EP": "PE", "TVP": "DVT",
                      "Positivo": "Positive", "Negativo": "Negative", "Elevada": "Elevated",
                      "No practicado": "Not performed"}))


def prepare_features(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return categorical pre-test features and a field-level quality audit.

    Missing history stays missing. ``Not performed`` D-dimer is an observed
    category, distinct from unknown. Out-of-range numeric measurements are set
    missing; quality bounds are analysis conventions, not diagnostic limits.
    Splanchnic absence requires all three source sites explicitly negative.
    """
    result = pd.DataFrame(index=raw.index)
    audit = []
    sentinel = np.iinfo(np.int64).min
    for col, label in CATEGORICAL.items():
        if col not in raw:
            continue
        result[col] = text_values(raw[col])
        audit.append(dict(variable=col, label=label, original_missing=int(raw[col].isna().sum()),
                          invalid_numeric=0, transformed_missing=int(result[col].isna().sum()),
                          rule="Recorded category; unknown remains missing"))
    for col, (lo, hi, bins, names, label) in NUMERIC.items():
        if col not in raw:
            continue
        values = pd.to_numeric(raw[col], errors="coerce").replace(sentinel, np.nan)
        bad = values.notna() & ~values.between(lo, hi)
        values = values.mask(bad)
        result[col] = pd.cut(values, bins, labels=names, right=False).astype("string")
        audit.append(dict(variable=col, label=label, original_missing=int(raw[col].isna().sum()),
                          invalid_numeric=int(bad.sum()), transformed_missing=int(result[col].isna().sum()),
                          rule=f"Valid range [{lo}, {hi}]; categories {names}; invalid -> missing"))
    if {"sexo", "edad"}.issubset(raw):
        age = pd.to_numeric(raw.edad, errors="coerce")
        valid = age.between(0, 120) & raw.sexo.notna()
        result["female_under45"] = pd.Series(pd.NA, index=raw.index, dtype="string")
        result.loc[valid, "female_under45"] = np.where(
            raw.loc[valid, "sexo"].isin(["Mujer", "Female"]) & (age[valid] < 45), "Yes", "No")
    sites = [c for c in ["tv_l_vpo", "tv_l_vme", "tv_l_ves"] if c in raw]
    if len(sites) == 3:
        vals = raw[sites].apply(text_values)
        result["splanchnic"] = pd.Series(pd.NA, index=raw.index, dtype="string")
        result.loc[vals.eq("No").fillna(False).all(axis=1), "splanchnic"] = "No"
        result.loc[vals.eq("Yes").fillna(False).any(axis=1), "splanchnic"] = "Yes"
    # No automatically eligible predictor is taken from an outcome/follow-up field.
    assert not any(c.startswith(("evn_", "eisq_")) for c in result)
    assert not set(result) & ({o.column for o in OUTCOMES} | {"ana_port", "e_con_af", "ddvalmcg"})
    return result, pd.DataFrame(audit)


def tested_mask(raw: pd.DataFrame) -> pd.Series:
    """Study status is documented positive/negative; unknown is not evidence of testing."""
    return raw.ana_dura.astype("string").isin(TESTED)


def known_thrombophilia_mask(raw: pd.DataFrame) -> pd.Series:
    """Exclude explicit pre-existing carrier status or known APS; never infer from nulls."""
    return text_values(raw.ana_port).eq("Yes").fillna(False) | text_values(raw.e_con_af).eq("Yes").fillna(False)


def outcome_mask(raw: pd.DataFrame, outcome: Outcome) -> pd.Series:
    """Require documented global testing and binary subtype; exclude known carriers.

    Binary subtype coding is the operational eligibility definition. The extract
    has no independent assay-performed flag, so it cannot prove that every No
    represents a laboratory-confirmed negative. Reports retain this limitation.
    """
    negative = TESTED[1] if outcome.column == "ana_dura" else "No"
    return (tested_mask(raw) & ~known_thrombophilia_mask(raw)
            & raw[outcome.column].astype("string").isin([outcome.positive, negative]))


def missingness_table(raw: pd.DataFrame, features: pd.DataFrame, mask: pd.Series, group: str) -> pd.DataFrame:
    """Quantify missingness before modelling, with not-performed counts kept separate."""
    rows = []
    for col in features:
        s = features.loc[mask, col]
        source = raw.loc[mask, col] if col in raw else s
        rows.append(dict(group=group, variable=col, label=LABELS[col], n=len(s),
                         source_null_n=int(source.isna().sum()), missing_n=int(s.isna().sum()),
                         missing_pct=100 * s.isna().mean(),
                         not_performed_n=int(s.eq("Not performed").fillna(False).sum())))
    return pd.DataFrame(rows)
