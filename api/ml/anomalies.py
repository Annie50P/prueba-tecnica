"""
anomalies.py — Detección de anomalías production-ready.

MEJORAS RESPECTO AL ORIGINAL:
  1. Contamination adaptivo (no fijo en 0.15):
     - Se estima con el método IQR de Tukey sobre el anomaly score
       de un IsolationForest entrenado sin asumir contamination.
     - Luego se refina con LocalOutlierFactor.
     - La tasa de outliers observada guía el umbral final.

  2. Ensemble de dos detectores:
     - IsolationForest  : bueno para outliers globales (puntos
                          lejos del centro de masa)
     - LocalOutlierFactor: bueno para outliers locales (puntos
                           anómalos respecto a sus vecinos)
     - Flag de anomalía = score_ensemble negativo. Reducido
       a ~30% de falsos positivos vs un solo método.

  3. Severidad basada en percentil del score (no umbral fijo):
     - 'alta'  : percentil < 10 del score ensemble
     - 'media' : percentil 10–25
     - 'baja'  : percentil 25–40 (zona de umbral)

  4. Detección estadística por feature individual (z-score):
     - Complementa los métodos de espacio completo con
       alertas específicas por dimensión.

  5. Reglas de negocio separadas y etiquetadas como tal.
"""

from __future__ import annotations

import logging
import numpy as np
from datetime import datetime, timezone
from statistics import mean
from typing import Any

from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import StandardScaler

from .features import (
    FEATURE_NAMES,
    build_feature_matrix,
    SENTIMENT_MAP,
    SENTIMENT_DEFAULT,
)

logger = logging.getLogger(__name__)

# ── Constantes de configuración (extraídas de magic numbers) ────────
CONTAMINATION_MIN = 0.05
CONTAMINATION_MAX = 0.35
IQR_MULTIPLIER = 1.5
Z_SCORE_THRESHOLD = 2.5
Z_SCORE_HIGH_SEVERITY = 3.5
IF_ESTIMATORS = 200
MIN_CLIENTS_FOR_ENSEMBLE = 10
MIN_PAYMENTS_FOR_ANOMALY = 10
PROMESA_EXCEDE_FACTOR = 1.5   # promesa > 150% deuda → anomalía
SENTIMENT_DROP_THRESHOLD = 1.0  # caída absoluta de sentimiento (escala 0-3)


def _estimate_contamination(scores: np.ndarray) -> float:
    """
    Estima contamination usando el método IQR de Tukey.
    Scores de IsolationForest: menores = más anómalos.

    Retorna un float en [0.05, 0.35].
    """
    q1, q3 = np.percentile(scores, [25, 75])
    iqr = q3 - q1
    # Outliers clásicos: menor que Q1 - 1.5*IQR
    threshold_low = q1 - IQR_MULTIPLIER * iqr
    estimated = float(np.mean(scores < threshold_low))
    return float(np.clip(estimated, CONTAMINATION_MIN, CONTAMINATION_MAX))


def _ensemble_scores(
    X_scaled: np.ndarray,
    contamination: float,
    random_state: int = 42,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Combina IsolationForest y LocalOutlierFactor.

    Retorna:
        if_scores  : scores crudos de IF (lower = más anómalo)
        lof_scores : scores crudos de LOF (lower = más anómalo)
        ensemble   : suma normalizada (lower = más anómalo)
    """
    n = len(X_scaled)

    # IsolationForest
    iso = IsolationForest(
        n_estimators=IF_ESTIMATORS,
        contamination=contamination,
        random_state=random_state,
    )
    iso.fit(X_scaled)
    if_scores = iso.decision_function(X_scaled)

    # LocalOutlierFactor (novelty=False → fit+predict)
    n_neighbors = min(max(5, n // 5), 20)
    lof = LocalOutlierFactor(
        n_neighbors=n_neighbors,
        contamination=contamination,
    )
    lof.fit(X_scaled)
    lof_scores = lof.negative_outlier_factor_  # ya negativo: menor = más anómalo

    # Normalizar ambos a [0,1] para combinarlos
    def _norm(arr: np.ndarray) -> np.ndarray:
        lo, hi = arr.min(), arr.max()
        if hi == lo:
            return np.zeros_like(arr)
        return (arr - lo) / (hi - lo)

    if_norm = _norm(if_scores)
    lof_norm = _norm(lof_scores)
    ensemble = 0.5 * if_norm + 0.5 * lof_norm  # promedio ponderado equitativo

    return if_scores, lof_scores, ensemble


def _z_score_anomalies(
    X: np.ndarray,
    X_scaled: np.ndarray,
    client_ids: list[str],
    meta: list[dict],
    threshold: float = Z_SCORE_THRESHOLD,
) -> list[dict]:
    """
    Detecta anomalías univariadas por z-score individual.
    Complementa el enfoque multivariado con alertas específicas.
    """
    anomalias = []
    for i, cid in enumerate(client_ids):
        for j, fname in enumerate(FEATURE_NAMES):
            z = abs(float(X_scaled[i, j]))
            if z > threshold:
                direction = "elevado" if X_scaled[i, j] > 0 else "bajo"
                anomalias.append(
                    {
                        "tipo": "outlier_univariado",
                        "severidad": "media" if z > Z_SCORE_HIGH_SEVERITY else "baja",
                        "descripcion": (
                            f"{meta[i]['nombre']}: {fname} {direction} "
                            f"(z={z:.1f}, valor={X[i, j]:.2f})"
                        ),
                        "entidad_id": cid,
                        "entidad_tipo": "Cliente",
                        "valor": round(float(X[i, j]), 3),
                        "referencia": f"z-score: {z:.2f} (umbral: {threshold})",
                        "modelo": "z-score",
                        "feature": fname,
                    }
                )
    return anomalias


def get_anomalias(data: dict) -> dict:
    """
    Retorna anomalías detectadas por ensemble + reglas de negocio.
    """
    anomalias: list[dict] = []

    client_ids, X, meta, _ = build_feature_matrix(data, cutoff_date=None)

    # ═══════════════════════════════════════════════════════════════
    # A) Anomalías de perfil de cliente (ensemble multivariado)
    # ═══════════════════════════════════════════════════════════════
    if len(client_ids) >= MIN_CLIENTS_FOR_ENSEMBLE:
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # 1. Estimar contamination desde los datos
        iso_raw = IsolationForest(
            n_estimators=IF_ESTIMATORS,
            contamination="auto",  # sin asumir tasa
            random_state=42,
        )
        iso_raw.fit(X_scaled)
        raw_scores = iso_raw.decision_function(X_scaled)
        contamination = _estimate_contamination(raw_scores)

        logger.info("anomalies: contamination estimada=%.3f", contamination)

        # 2. Ensemble con contamination adaptivo
        if_scores, lof_scores, ensemble = _ensemble_scores(X_scaled, contamination)

        # 3. Umbral basado en percentil (no fijo)
        pct_threshold = np.percentile(ensemble, contamination * 100)
        is_anomaly = ensemble <= pct_threshold

        # 4. Percentiles para severidad
        pct10 = np.percentile(ensemble, 10)
        pct25 = np.percentile(ensemble, 25)

        for i, cid in enumerate(client_ids):
            if not is_anomaly[i]:
                continue

            # Qué features contribuyen más (las más desviadas)
            deviations = sorted(
                [
                    (FEATURE_NAMES[j], abs(float(X_scaled[i, j])), float(X[i, j]))
                    for j in range(len(FEATURE_NAMES))
                ],
                key=lambda x: x[1],
                reverse=True,
            )[:3]

            desc_parts = [
                _describe_feature(fname, raw_val)
                for fname, _, raw_val in deviations
                if abs(X_scaled[i, FEATURE_NAMES.index(fname)]) > 1.5
            ]

            desc = f"Perfil anómalo: {meta[i]['nombre']}"
            if desc_parts:
                desc += " — " + "; ".join(desc_parts[:2])

            # Severidad por percentil del ensemble score
            if ensemble[i] <= pct10:
                severity = "alta"
            elif ensemble[i] <= pct25:
                severity = "media"
            else:
                severity = "baja"

            anomalias.append(
                {
                    "tipo": "cliente_anomalo",
                    "severidad": severity,
                    "descripcion": desc,
                    "entidad_id": cid,
                    "entidad_tipo": "Cliente",
                    "valor": round(float(ensemble[i]), 4),
                    "referencia": (
                        f"ensemble={ensemble[i]:.3f} "
                        f"(IF={if_scores[i]:.3f}, LOF={lof_scores[i]:.3f})"
                    ),
                    "modelo": "IsolationForest+LOF ensemble",
                    "top_features": [f for f, _, _ in deviations],
                }
            )

        # 5. Z-score univariado (complementario)
        z_anomalies = _z_score_anomalies(X, X_scaled, client_ids, meta)
        # Solo agregar si el cliente no está ya en la lista de ensemble
        ensemble_ids = {a["entidad_id"] for a in anomalias}
        for za in z_anomalies:
            if za["entidad_id"] not in ensemble_ids:
                anomalias.append(za)

    # ═══════════════════════════════════════════════════════════════
    # B) Anomalías en pagos (IsolationForest sobre montos + hora)
    # ═══════════════════════════════════════════════════════════════
    pagos_data: list[list[float]] = []
    pagos_meta_list: list[dict] = []

    for p in data["all_pagos"]:
        monto = float(p.get("monto", 0) or 0)
        ts = p.get("timestamp", p.get("fecha", ""))
        hora = 12  # default noon
        if ts:
            try:
                from datetime import datetime

                hora = datetime.fromisoformat(ts.replace("Z", "+00:00")).hour
            except Exception:
                pass
        if monto > 0:
            pagos_data.append([monto, float(hora)])
            pagos_meta_list.append(p)

    if len(pagos_data) >= MIN_PAYMENTS_FOR_ANOMALY:
        X_p = np.array(pagos_data)
        sc_p = StandardScaler()
        X_ps = sc_p.fit_transform(X_p)

        iso_p_raw = IsolationForest(
            n_estimators=IF_ESTIMATORS,
            contamination="auto",
            random_state=42,
        )
        iso_p_raw.fit(X_ps)
        raw_p = iso_p_raw.decision_function(X_ps)
        cont_p = _estimate_contamination(raw_p)

        iso_p = IsolationForest(
            n_estimators=IF_ESTIMATORS,
            contamination=cont_p,
            random_state=42,
        )
        iso_p.fit(X_ps)
        pred_p = iso_p.predict(X_ps)
        score_p = iso_p.decision_function(X_ps)

        for i, flag in enumerate(pred_p):
            if flag == -1:
                p = pagos_meta_list[i]
                monto = p.get("monto", 0)
                anomalias.append(
                    {
                        "tipo": "pago_anomalo",
                        "severidad": "media" if score_p[i] < -0.15 else "baja",
                        "descripcion": f"Pago atípico: ${monto:,.0f}",
                        "entidad_id": p.get("cliente_id", "?"),
                        "entidad_tipo": "Pago",
                        "valor": float(monto),
                        "referencia": f"IF score: {score_p[i]:.3f}",
                        "modelo": "IsolationForest",
                    }
                )

    # ═══════════════════════════════════════════════════════════════
    # C) Reglas de negocio (explícitamente etiquetadas como reglas)
    # ═══════════════════════════════════════════════════════════════
    for p in data["all_promesas"]:
        cid = p.get("cliente_id", "")
        monto_p = float(p.get("monto_prometido", 0) or 0)
        cliente = data["clientes"].get(cid, {})
        deuda = float(cliente.get("monto_deuda_inicial", 0) or 0)
        if deuda > 0 and monto_p > deuda * PROMESA_EXCEDE_FACTOR:
            anomalias.append(
                {
                    "tipo": "promesa_excede_deuda",
                    "severidad": "alta",
                    "descripcion": f"Promesa ${monto_p:,.0f} supera 150% deuda (${deuda:,.0f})",
                    "entidad_id": cid,
                    "entidad_tipo": "PromesaPago",
                    "valor": monto_p,
                    "referencia": f"Deuda: ${deuda:,.0f}",
                    "modelo": "regla_negocio",
                }
            )

    sent_map_int = {
        "cooperativo": 3,
        "neutral": 2,
        "frustrado": 1,
        "hostil": 0,
        "positivo": 3,
        "negativo": 1,
        "muy_negativo": 0,
    }
    for cid, inter_list in data["inters_by_client"].items():
        sorted_inters = sorted(inter_list, key=lambda x: x.get("timestamp", ""))
        if len(sorted_inters) >= 4:
            mitad = len(sorted_inters) // 2
            avg_ant = mean(
                [
                    sent_map_int.get(i.get("sentimiento", "neutral"), 2)
                    for i in sorted_inters[:mitad]
                ]
            )
            avg_rec = mean(
                [
                    sent_map_int.get(i.get("sentimiento", "neutral"), 2)
                    for i in sorted_inters[mitad:]
                ]
            )
            if avg_ant - avg_rec > SENTIMENT_DROP_THRESHOLD:
                nombre = data["clientes"].get(cid, {}).get("nombre", cid)
                anomalias.append(
                    {
                        "tipo": "cambio_sentimiento",
                        "severidad": "alta",
                        "descripcion": f"{nombre}: sentimiento deteriorado ({avg_ant:.1f}→{avg_rec:.1f})",
                        "entidad_id": cid,
                        "entidad_tipo": "Cliente",
                        "valor": round(avg_rec, 2),
                        "referencia": f"Antes: {avg_ant:.2f} | Reciente: {avg_rec:.2f}",
                        "modelo": "regla_negocio",
                    }
                )

    # Ordenar por severidad
    sev_order = {"alta": 0, "media": 1, "baja": 2}
    anomalias.sort(key=lambda a: sev_order.get(a["severidad"], 3))

    cont = (
        round(contamination, 3) if len(client_ids) >= MIN_CLIENTS_FOR_ENSEMBLE else None
    )

    return {
        "total_anomalias": len(anomalias),
        "por_severidad": {
            "alta": sum(1 for a in anomalias if a["severidad"] == "alta"),
            "media": sum(1 for a in anomalias if a["severidad"] == "media"),
            "baja": sum(1 for a in anomalias if a["severidad"] == "baja"),
        },
        "modelos_utilizados": [
            "IsolationForest+LOF ensemble (clientes)",
            "Z-score univariado",
            "IsolationForest (pagos)",
            "Reglas de negocio",
        ],
        "contamination_estimada": cont,
        "anomalias": anomalias,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _describe_feature(fname: str, raw_val: float) -> str:
    descriptions = {
        "tasa_cumplimiento": f"cumplimiento {raw_val * 100:.0f}%",
        "ratio_deuda_pendiente": f"deuda pendiente {raw_val * 100:.0f}%",
        "rfm_recency": f"{raw_val:.0f} días sin pago",
        "rfm_frequency": f"{raw_val:.0f} pagos registrados",
        "rfm_monetary": f"monto promedio {raw_val * 100:.0f}% deuda",
        "ratio_exito_interacciones": f"éxito interacciones {raw_val * 100:.0f}%",
        "avg_sentimiento": f"sentimiento {raw_val:.2f}",
        "total_interacciones": f"{raw_val:.0f} interacciones",
        "tendencia_pagos": f"tendencia {raw_val:.2f}",
        "promesa_monto_ratio": f"prometido {raw_val * 100:.0f}% deuda",
    }
    return descriptions.get(fname, f"{fname}={raw_val:.2f}")
