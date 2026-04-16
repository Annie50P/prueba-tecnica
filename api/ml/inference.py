"""
inference.py — Predicciones con el modelo entrenado.

Funciones expuestas:
  - run_inference(): realiza predicciones sobre todos los clientes
  - explain(): genera explicaciones legibles por cliente
"""

from __future__ import annotations

import numpy as np
from typing import Any

from .features import FEATURE_NAMES


def explain(features: np.ndarray) -> list[str]:
    """Genera explicaciones legibles basadas en thresholds."""
    explanations = []

    tasa_cumpl = features[0]
    ratio_pend = features[1]
    rfm_recency = features[2]
    rfm_frequency = features[3]
    rfm_monetary = features[4]
    ratio_exito = features[5]
    avg_sent = features[6]
    tendencia = features[8]

    if tasa_cumpl < 0.15:
        explanations.append(f"Muy baja tasa de cumplimiento ({tasa_cumpl * 100:.0f}%)")
    elif tasa_cumpl < 0.4:
        explanations.append(f"Baja tasa de cumplimiento ({tasa_cumpl * 100:.0f}%)")

    if ratio_pend > 0.85:
        explanations.append(f"{ratio_pend * 100:.0f}% de la deuda aún pendiente")

    if rfm_frequency == 0:
        explanations.append("Sin pagos registrados")
    elif rfm_recency > 60:
        explanations.append(f"Último pago hace {rfm_recency:.0f} días")

    if ratio_exito < 0.2 and ratio_exito > 0:
        explanations.append(f"Solo {ratio_exito * 100:.0f}% de interacciones exitosas")
    elif ratio_exito == 0 and rfm_frequency == 0:
        explanations.append("Sin interacciones exitosas")

    if avg_sent < 0.3:
        explanations.append("Sentimiento predominantemente hostil/frustrado")

    if tendencia < 0.3 and rfm_frequency >= 2:
        explanations.append("Tendencia decreciente en montos de pago")

    if not explanations:
        if rfm_monetary > 0.3:
            explanations.append(
                f"Pagos consistentes ({rfm_monetary * 100:.0f}% del saldo promedio)"
            )
        elif tasa_cumpl > 0.7:
            explanations.append(f"Alta tasa de cumplimiento ({tasa_cumpl * 100:.0f}%)")
        else:
            explanations.append("Perfil de riesgo moderado")

    return explanations


def run_inference(
    client_ids: list[str],
    X: np.ndarray,
    meta: list[dict],
    model_info: dict[str, Any],
) -> list[dict]:
    """
    Realiza predicciones con el modelo ya entrenado.
    model_info debe contener: best_model, scaler, label_mode.
    """
    model = model_info.get("best_model")
    scaler = model_info.get("scaler")
    label_mode = model_info.get("label_mode", "unknown")

    if model is None or scaler is None:
        raise ValueError("model_info debe contener best_model y scaler")

    X_scaled = scaler.transform(X)
    proba = model.predict_proba(X_scaled)

    # Obtener índice de clase positiva
    try:
        classes = list(getattr(model, "classes_", [0, 1]))
        if 1 in classes:
            idx_pos = classes.index(1)
        else:
            idx_pos = 1 if len(classes) > 1 else 0
    except Exception:
        idx_pos = 1

    results = []
    for i, cid in enumerate(client_ids):
        prob_pago = round(float(proba[i][idx_pos]) * 100, 1)
        score_riesgo = round(100 - prob_pago, 1)

        if score_riesgo >= 70:
            categoria = "alto"
        elif score_riesgo >= 40:
            categoria = "medio"
        else:
            categoria = "bajo"

        results.append(
            {
                "cliente_id": cid,
                "score_riesgo": score_riesgo,
                "categoria_riesgo": categoria,
                "probabilidad_pago": prob_pago,
                "label_mode": label_mode,
                "factores": explain(X[i]),
            }
        )

    results.sort(key=lambda x: x["score_riesgo"], reverse=True)
    return results
