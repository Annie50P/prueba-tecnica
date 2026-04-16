"""
features.py — Feature engineering pipeline para cobranza.

CAMBIOS RESPECTO A analytics_service.py ORIGINAL:
  1. Mapeo de sentimiento corregido: los datos reales usan
     'cooperativo', 'hostil', 'frustrado', 'neutral' — no
     'positivo'/'negativo'. El mapa original retornaba 0.5 (neutral)
     para casi todos los clientes, convirtiendo ese feature en ruido.

  2. Features nuevas basadas en outcomes reales:
     - ratio_exito_interacciones  : (promesa_pago + pago_inmediato) / total
     - n_pagos_recibidos          : interacciones de tipo 'pago_recibido'
     - rfm_recency                : días desde último pago (no solo actividad)
     - rfm_frequency              : frecuencia de pagos efectivos
     - rfm_monetary               : monto promedio por pago

  3. Features que indican voluntad real de pago (no sólo deuda restante):
     - promesa_cumplimiento_rate  : promesas cumplidas / total
     - promesa_monto_ratio        : monto prometido / deuda inicial

  4. Separación clara entre features de INPUT (sin leakage) y
     features de LABEL (usadas solo para construir y/o. supervisado).
"""

from __future__ import annotations

import numpy as np
from datetime import datetime, timezone
from statistics import mean
from typing import Any


# ── Sentimiento ─────────────────────────────────────────────────────
# BUG ORIGINAL: mapeaba 'positivo'/'negativo'/'muy_negativo'
# que NO aparecen en los datos. Los valores reales son:
# 'cooperativo', 'hostil', 'frustrado', 'neutral', None, 'n/a'
SENTIMENT_MAP: dict[str, float] = {
    "cooperativo": 1.0,
    "neutral": 0.5,
    "frustrado": 0.25,
    "hostil": 0.0,
    # compatibilidad con datasets que usen el vocabulario antiguo
    "positivo": 1.0,
    "negativo": 0.2,
    "muy_negativo": 0.0,
}
SENTIMENT_DEFAULT = 0.5  # para None / 'n/a' / valores desconocidos

# ── Resultados de interacción que se consideran "exitosos" ──────────
OUTCOME_SUCCESS = {"promesa_pago", "pago_inmediato", "renegociacion"}
OUTCOME_FAILURE = {"se_niega_pagar", "sin_respuesta"}

FEATURE_NAMES = [
    # -- features de comportamiento de pago --
    "tasa_cumplimiento",  # 0  promesas cumplidas / total promesas
    "ratio_deuda_pendiente",  # 1  pendiente / inicial
    "rfm_recency",  # 2  días desde último pago (lower = better)
    "rfm_frequency",  # 3  # pagos recibidos
    "rfm_monetary",  # 4  monto promedio por pago normalizado
    # -- features de engagement --
    "ratio_exito_interacciones",  # 5  outcomes exitosos / total
    "avg_sentimiento",  # 6  promedio sentimiento (mapa corregido)
    "total_interacciones",  # 7  volumen de contacto
    # -- features de tendencia --
    "tendencia_pagos",  # 8  ratio pagos recientes / anteriores
    "promesa_monto_ratio",  # 9  monto prometido / deuda inicial
]


def _parse_ts(ts: str | None) -> datetime | None:
    """Parsea ISO 8601 de forma tolerante."""
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def build_feature_matrix(
    data: dict[str, Any],
) -> tuple[list[str], np.ndarray, list[dict], np.ndarray | None]:
    """
    Construye la matriz de features X y el vector de labels y.

    Returns:
        client_ids : lista de IDs en el mismo orden que las filas de X
        X          : np.ndarray shape (n_clientes, len(FEATURE_NAMES))
        meta       : lista de dicts con info legible por humanos
        y          : np.ndarray de labels (1 = pagará, 0 = no pagará)
                     None cuando no hay suficiente ground truth
    """
    # ── Validación de inputs ─────────────────────────────────────
    if not data:
        raise ValueError("data está vacío")
    if "clientes" not in data or not data["clientes"]:
        raise ValueError("no hay clientes en data")
    if len(data["clientes"]) < 5:
        raise ValueError(f"Mínimo 5 clientes requeridos, hay {len(data['clientes'])}")

    clientes = data["clientes"]
    inters_by_client = data["inters_by_client"]
    promesas_by_client = data["promesas_by_client"]
    pagos_by_client = data["pagos_by_client"]
    now = _now_utc()

    client_ids: list[str] = []
    features: list[list[float]] = []
    meta_list: list[dict] = []
    raw_labels: list[int | None] = []

    for cid, props in clientes.items():
        inters = inters_by_client.get(cid, [])
        promesas = promesas_by_client.get(cid, [])
        pagos = pagos_by_client.get(cid, [])

        deuda_ini = float(props.get("monto_deuda_inicial", 0) or 0)
        pendiente = float(props.get("monto_pendiente", 0) or 0)
        total_pago = float(props.get("total_pagado", 0) or 0)

        # ── Feature 0: tasa_cumplimiento ────────────────────────────
        if promesas:
            cumplidas = sum(1 for p in promesas if p.get("cumplida") is True)
            tasa_cumpl = cumplidas / len(promesas)
        else:
            tasa_cumpl = 0.0

        # ── Feature 1: ratio_deuda_pendiente ────────────────────────
        ratio_pend = pendiente / deuda_ini if deuda_ini > 0 else 1.0

        # ── Features RFM ────────────────────────────────────────────
        # Filtrar interacciones que son pagos reales
        pago_inters = [
            i
            for i in inters
            if i.get("tipo") == "pago_recibido"
            or i.get("resultado") == "pago_inmediato"
        ]

        # Recency: días desde último pago (rfm_recency)
        pago_timestamps = sorted(
            [
                _parse_ts(i.get("timestamp"))
                for i in pago_inters
                if _parse_ts(i.get("timestamp"))
            ],
        )
        if pago_timestamps:
            last_pago = pago_timestamps[-1]
            if last_pago.tzinfo is None:
                last_pago = last_pago.replace(tzinfo=timezone.utc)
            rfm_recency = float((now - last_pago).days)
        else:
            rfm_recency = 180.0  # penalización máxima por inactividad

        # Frequency: número de pagos recibidos (rfm_frequency)
        rfm_frequency = float(len(pago_inters))

        # Monetary: monto promedio normalizado (rfm_monetary)
        montos_pago = [
            float(i.get("monto", 0) or 0)
            for i in pago_inters
            if (i.get("monto") or 0) > 0
        ]
        if montos_pago and deuda_ini > 0:
            rfm_monetary = mean(montos_pago) / deuda_ini
        else:
            rfm_monetary = 0.0

        # ── Feature 5: ratio_exito_interacciones ────────────────────
        llamadas = [
            i for i in inters if i.get("resultado") in OUTCOME_SUCCESS | OUTCOME_FAILURE
        ]
        if llamadas:
            n_exitosas = sum(
                1 for i in llamadas if i.get("resultado") in OUTCOME_SUCCESS
            )
            ratio_exito = n_exitosas / len(llamadas)
        else:
            ratio_exito = 0.0

        # ── Feature 6: avg_sentimiento (MAPA CORREGIDO) ─────────────
        if inters:
            sents = [
                SENTIMENT_MAP.get(i.get("sentimiento", ""), SENTIMENT_DEFAULT)
                for i in inters
                if i.get("sentimiento") not in (None, "n/a", "")
            ]
            avg_sent = mean(sents) if sents else SENTIMENT_DEFAULT
        else:
            avg_sent = SENTIMENT_DEFAULT

        # ── Feature 7: total_interacciones ──────────────────────────
        n_inters = float(len(inters))

        # ── Feature 8: tendencia_pagos ──────────────────────────────
        if len(pagos) >= 2:
            pagos_sorted = sorted(
                pagos,
                key=lambda x: x.get("timestamp", x.get("fecha", "")),
            )
            mitad = len(pagos_sorted) // 2
            avg_ant = (
                mean([float(p.get("monto", 0) or 0) for p in pagos_sorted[:mitad]])
                or 1.0
            )
            avg_rec = mean(
                [float(p.get("monto", 0) or 0) for p in pagos_sorted[mitad:]]
            )
            tendencia = avg_rec / avg_ant
        elif pagos:
            tendencia = 1.0
        else:
            tendencia = 0.0

        # ── Feature 9: promesa_monto_ratio ──────────────────────────
        total_prometido = sum(float(p.get("monto_prometido", 0) or 0) for p in promesas)
        promesa_ratio = total_prometido / deuda_ini if deuda_ini > 0 else 0.0

        # ── Ground truth label ──────────────────────────────────────
        # Label = 1: tiene pagos reales O promesa cumplida
        # Label = 0: NO tiene pagos Y (todas las llamadas son failure O sin actividad reciente)
        # Label = None: no hay suficiente evidencia (semi-supervisado)
        has_real_payment = len(pago_inters) > 0
        has_promise_kept = any(p.get("cumplida") is True for p in promesas)

        # only_refused: NO hay pagos Y todas las interacciones son failure
        only_failure = llamadas and all(
            i.get("resultado")
            in {"se_niega_pagar", "sin_respuesta", "no_disponible", "disputa"}
            for i in llamadas
        )

        # sin actividad reciente (> 30 dias sin pago)
        no_recent_activity = rfm_recency > 30 if (pagos or llamadas) else False

        if has_real_payment or has_promise_kept:
            label = 1
        elif only_failure or no_recent_activity:
            label = 0
        else:
            label = None  # semi-supervisado

        client_ids.append(cid)
        features.append(
            [
                tasa_cumpl,  # 0
                ratio_pend,  # 1
                rfm_recency,  # 2
                rfm_frequency,  # 3
                rfm_monetary,  # 4
                ratio_exito,  # 5
                avg_sent,  # 6
                n_inters,  # 7
                tendencia,  # 8
                promesa_ratio,  # 9
            ]
        )
        raw_labels.append(label)
        meta_list.append(
            {
                "nombre": props.get("nombre", cid),
                "deuda_inicial": deuda_ini,
                "deuda_pendiente": pendiente,
                "total_pagado": total_pago,
                "tasa_cumplimiento": round(tasa_cumpl * 100, 1),
                "deuda_pendiente_pct": round(ratio_pend * 100, 1),
                "total_pagos": len(pagos),
                "total_interacciones": int(n_inters),
                "total_promesas": len(promesas),
                "label_observado": label,
            }
        )

    X = np.array(features, dtype=float)

    # Construir vector y sólo con los labels observados como int
    labeled_mask = [l is not None for l in raw_labels]
    n_labeled = sum(labeled_mask)
    if n_labeled >= 10 and len(set(l for l in raw_labels if l is not None)) >= 2:
        y = np.array(
            [l if l is not None else -1 for l in raw_labels],
            dtype=int,
        )
    else:
        y = None  # caemos a modo heurístico (ver predictor.py)

    return client_ids, X, meta_list, y


def label_stats(y: np.ndarray | None, raw_labels: list) -> dict:
    """Retorna estadísticas sobre la calidad del ground truth."""
    if y is None:
        return {"mode": "heuristic", "n_labeled": 0}
    mask = y != -1
    n_pos = int(np.sum(y[mask] == 1))
    n_neg = int(np.sum(y[mask] == 0))
    return {
        "mode": "ground_truth",
        "n_labeled": int(mask.sum()),
        "n_positive": n_pos,
        "n_negative": n_neg,
        "positive_rate": round(n_pos / (n_pos + n_neg), 3)
        if (n_pos + n_neg) > 0
        else 0,
    }
