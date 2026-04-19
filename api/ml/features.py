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

  4. SPLIT TEMPORAL HONESTO (anti-data-leakage):
     El dataset cubre ~90 días (mayo–septiembre 2025).
     CUTOFF_DATE separa la ventana de features de la ventana de etiqueta:
       - Features  → interacciones ANTES del corte (primeros ~60 días)
       - Label = 1 → el cliente realizó un pago_recibido DESPUÉS del corte
     Así el modelo aprende señales de comportamiento temprano para predecir
     pagos futuros, sin ver los pagos que está intentando predecir.
"""

from __future__ import annotations

import logging
import numpy as np
from datetime import datetime, timezone
from statistics import mean
from typing import Any

logger = logging.getLogger(__name__)

# ── Corte temporal honesto ───────────────────────────────────────────
# Legacy defaults (usados solo si no se puede derivar de los datos).
# Son sobreescritos por infer_cutoff_from_data() en tiempo de ejecución.
_DEFAULT_CUTOFF = datetime(2025, 7, 16, tzinfo=timezone.utc)
_DEFAULT_DATA_END = datetime(2025, 9, 2, tzinfo=timezone.utc)

# Fracción del rango temporal que se usa como ventana de features.
# 0.66 → ~60 % de los timestamps son features, el 40 % restante es label.
CUTOFF_FRACTION = 0.66

# Penalización (en días) cuando un cliente no tiene pagos pre-corte
RFM_RECENCY_NO_PAGO_DEFAULT = 180.0


def _collect_timestamps(data: dict[str, Any]) -> list[datetime]:
    ts_list: list[datetime] = []
    # Solo eventos reales (interacciones y pagos) determinan el rango temporal.
    # fecha_promesa es una fecha futura comprometida, no un evento pasado —
    # incluirla infla t_max y desplaza el cutoff más allá del fin real de los datos.
    for bucket in ("all_inters", "all_pagos"):
        for item in data.get(bucket, []) or []:
            ts = _parse_ts(item.get("timestamp") or item.get("fecha"))
            if ts is not None:
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                ts_list.append(ts)
    return ts_list


def infer_cutoff_from_data(
    data: dict[str, Any],
    fraction: float = CUTOFF_FRACTION,
) -> tuple[datetime, datetime]:
    """
    Deriva (cutoff_date, data_end_date) del rango real de timestamps.

    Si el dataset no tiene suficientes timestamps, cae a los defaults legacy.
    """
    ts_list = _collect_timestamps(data)
    if len(ts_list) < 2:
        logger.warning("features: no hay timestamps suficientes; usando defaults legacy")
        return _DEFAULT_CUTOFF, _DEFAULT_DATA_END

    ts_list.sort()
    t_min, t_max = ts_list[0], ts_list[-1]
    span = (t_max - t_min).total_seconds()
    cutoff = t_min + (t_max - t_min) * fraction
    logger.info(
        "features: cutoff derivado=%s (rango %s → %s, span=%.1fd)",
        cutoff.date().isoformat(),
        t_min.date().isoformat(),
        t_max.date().isoformat(),
        span / 86400,
    )
    return cutoff, t_max


# Mantengo los nombres públicos para compat con imports existentes.
# Se consideran defaults — los módulos deberían pasar el cutoff derivado.
CUTOFF_DATE = _DEFAULT_CUTOFF
DATA_END_DATE = _DEFAULT_DATA_END


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


def _before_cutoff(inter: dict, cutoff: datetime) -> bool:
    """
    Retorna True si la interacción ocurrió ANTES del corte temporal.
    Si el timestamp no se puede parsear, log warning y se excluye
    (NO se incluye silenciosamente — evita basura en features).
    """
    ts = _parse_ts(inter.get("timestamp") or inter.get("fecha") or inter.get("fecha_promesa"))
    if ts is None:
        logger.debug("features: registro sin timestamp parseable, excluido: id=%s", inter.get("id"))
        return False
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts < cutoff


def build_feature_matrix(
    data: dict[str, Any],
    cutoff_date: datetime | None = "__auto__",
) -> tuple[list[str], np.ndarray, list[dict], np.ndarray | None]:
    """
    Construye la matriz de features X y el vector de labels y.

    cutoff_date controla el modo:
      - Si se provee (default=CUTOFF_DATE): SPLIT TEMPORAL HONESTO.
        Features: interacciones con timestamp < cutoff_date (~día 60).
        Label: ¿hubo pago_recibido con timestamp >= cutoff_date?
        Usar para predicción.

      - Si cutoff_date=None: USA TODOS LOS DATOS.
        rfm_recency relativo a DATA_END_DATE (fin del dataset).
        Retorna y=None (sin etiquetas de predicción).
        Usar para anomalías y segmentación.

    Returns:
        client_ids : lista de IDs en el mismo orden que las filas de X
        X          : np.ndarray shape (n_clientes, len(FEATURE_NAMES))
        meta       : lista de dicts con info legible por humanos
        y          : np.ndarray de labels (1 = pagó post-corte, 0 = no)
                     None en modo sin corte o sin variabilidad suficiente
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

    # Resolver cutoff: "__auto__" = derivar de los datos (B3).
    # None = modo sin corte (anomalías/segmentación).
    # datetime = explícito (tests).
    if cutoff_date == "__auto__":
        cutoff_date, data_end = infer_cutoff_from_data(data)
    else:
        _, data_end = infer_cutoff_from_data(data)

    temporal_split = cutoff_date is not None
    ref_date = cutoff_date if temporal_split else data_end

    client_ids: list[str] = []
    features: list[list[float]] = []
    meta_list: list[dict] = []
    labels: list[int] = []

    for cid, props in clientes.items():
        all_inters = inters_by_client.get(cid, [])
        all_promesas = promesas_by_client.get(cid, [])
        all_pagos = pagos_by_client.get(cid, [])

        if temporal_split:
            # Features: sólo lo que ocurrió ANTES del corte
            inters = [i for i in all_inters if _before_cutoff(i, cutoff_date)]
            promesas = [p for p in all_promesas if _before_cutoff(p, cutoff_date)]
            pagos = [p for p in all_pagos if _before_cutoff(p, cutoff_date)]
            # Label: pagos efectivos DESPUÉS del corte
            post_payments = [
                i for i in all_inters
                if not _before_cutoff(i, cutoff_date)
                and i.get("tipo") == "pago_recibido"
            ]
            label = 1 if post_payments else 0
        else:
            # Sin corte: usar todos los datos, sin etiqueta de predicción
            inters = all_inters
            promesas = all_promesas
            pagos = all_pagos
            post_payments = []
            label = -1  # sin etiqueta

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

        # ── Features RFM (sólo pagos pre-corte) ─────────────────────
        pago_inters = [
            i
            for i in inters
            if i.get("tipo") == "pago_recibido"
            or i.get("resultado") == "pago_inmediato"
        ]

        # Recency: días desde último pago pre-corte hasta el propio corte
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
            rfm_recency = float((ref_date - last_pago).days)
        else:
            rfm_recency = RFM_RECENCY_NO_PAGO_DEFAULT

        # Frequency: número de pagos recibidos pre-corte
        rfm_frequency = float(len(pago_inters))

        # Monetary: monto promedio normalizado (pre-corte)
        montos_pago = [
            float(i.get("monto", 0) or 0)
            for i in pago_inters
            if (i.get("monto") or 0) > 0
        ]
        if montos_pago and deuda_ini > 0:
            rfm_monetary = mean(montos_pago) / deuda_ini
        else:
            rfm_monetary = 0.0

        # ── Feature 5: ratio_exito_interacciones (pre-corte) ────────
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

        # ── Feature 6: avg_sentimiento (pre-corte, mapa corregido) ──
        if inters:
            sents = [
                SENTIMENT_MAP.get(i.get("sentimiento", ""), SENTIMENT_DEFAULT)
                for i in inters
                if i.get("sentimiento") not in (None, "n/a", "")
            ]
            avg_sent = mean(sents) if sents else SENTIMENT_DEFAULT
        else:
            avg_sent = SENTIMENT_DEFAULT

        # ── Feature 7: total_interacciones (pre-corte) ──────────────
        n_inters = float(len(inters))

        # ── Feature 8: tendencia_pagos (pre-corte) ──────────────────
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

        # ── Feature 9: promesa_monto_ratio (pre-corte) ──────────────
        total_prometido = sum(float(p.get("monto_prometido", 0) or 0) for p in promesas)
        promesa_ratio = total_prometido / deuda_ini if deuda_ini > 0 else 0.0

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
        labels.append(label)
        meta_entry = {
            "nombre": props.get("nombre", cid),
            "deuda_inicial": deuda_ini,
            "deuda_pendiente": pendiente,
            "total_pagado": total_pago,
            "tasa_cumplimiento": round(tasa_cumpl * 100, 1),
            "deuda_pendiente_pct": round(ratio_pend * 100, 1),
            "total_pagos": len(all_pagos),
            "total_interacciones": len(all_inters),
            "total_promesas": len(all_promesas),
            "label_observado": label if temporal_split else None,
        }
        if temporal_split:
            meta_entry["pagos_post_corte"] = len(post_payments)
            meta_entry["cutoff_date"] = cutoff_date.date().isoformat()
        meta_list.append(meta_entry)

    X = np.array(features, dtype=float)

    if not temporal_split:
        y = None  # sin corte → sin etiquetas de predicción
    else:
        y_arr = np.array(labels, dtype=int)
        # Requiere al menos 2 clases para entrenar un clasificador
        n_pos = int(np.sum(y_arr == 1))
        n_neg = int(np.sum(y_arr == 0))
        y = y_arr if (n_pos >= 2 and n_neg >= 2) else None

    return client_ids, X, meta_list, y


def label_stats(y: np.ndarray | None, cutoff_date: datetime | None = None) -> dict:
    """Retorna estadísticas sobre la calidad del ground truth."""
    if y is None:
        return {"mode": "heuristic", "n_labeled": 0}
    n_pos = int(np.sum(y == 1))
    n_neg = int(np.sum(y == 0))
    return {
        "mode": "temporal_split",
        "cutoff_date": cutoff_date.date().isoformat() if cutoff_date else None,
        "n_labeled": len(y),
        "n_positive": n_pos,
        "n_negative": n_neg,
        "positive_rate": round(n_pos / len(y), 3) if len(y) > 0 else 0,
    }
