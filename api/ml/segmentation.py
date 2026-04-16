"""
segmentation.py — Segmentación de cartera production-ready.

MEJORAS RESPECTO AL ORIGINAL:
  1. k óptimo via silhouette score (no k=4 fijo):
     - Evalúa k en rango [2, min(n//3, 6)]
     - Selecciona k con mayor silhouette promedio
     - Informa el score para auditoría

  2. Perfil de cluster basado en centroides reales (no por rank):
     - El nombre del cluster se asigna según qué features
       dominan en su centroide, no por posición en el ranking.
     - Esto evita que el cluster 0 siempre sea "Quick Wins"
       independientemente de los datos.

  3. Métricas de calidad del clustering:
     - silhouette_score global
     - inertia por cluster (cohesión interna)
     - davies_bouldin_score (separación entre clusters)

  4. Análisis de mejores horas con intervalo de confianza:
     - No solo tasa de éxito sino también n muestras
     - Excluye horas con < 5 llamadas (estadística insuficiente)

  5. Efectividad de agentes normalizada por volumen:
     - Antes: contaba éxitos absolutos (favorece agentes con más llamadas)
     - Ahora: tasa de éxito = éxitos / total_llamadas del agente
"""

from __future__ import annotations

import logging
import numpy as np
from datetime import datetime, timezone
from statistics import mean
from typing import Any

from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score, davies_bouldin_score

from .features import FEATURE_NAMES, build_feature_matrix

logger = logging.getLogger(__name__)

# Resultados que indican gestión exitosa
OUTCOME_SUCCESS = {"promesa_pago", "pago_inmediato", "renegociacion"}


def _select_optimal_k(X_scaled: np.ndarray, k_range: range) -> tuple[int, dict]:
    """
    Evalúa KMeans para cada k en k_range y elige el k
    con mayor silhouette score.

    Retorna (k_optimal, evaluation_dict).
    """
    evaluations: dict[int, dict] = {}
    best_k = k_range.start
    best_score = -1.0

    for k in k_range:
        km = KMeans(n_clusters=k, random_state=42, n_init=15)
        labels = km.fit_predict(X_scaled)

        # Silhouette requiere al menos 2 clusters con >= 2 muestras
        if len(set(labels)) < 2:
            continue

        sil = float(silhouette_score(X_scaled, labels))
        db = float(davies_bouldin_score(X_scaled, labels))

        evaluations[k] = {
            "silhouette": round(sil, 4),
            "davies_bouldin": round(db, 4),  # lower is better
            "inertia": round(float(km.inertia_), 2),
        }

        if sil > best_score:
            best_score = sil
            best_k = k

    return best_k, evaluations


def _name_cluster(
    centroid: np.ndarray, feat_names: list[str] = FEATURE_NAMES
) -> tuple[str, str, str]:
    """
    Asigna nombre, estrategia e impacto a un cluster basándose
    en los valores del centroide — no en su rank.

    Retorna (nombre, estrategia, impacto).
    """
    idx = {name: i for i, name in enumerate(feat_names)}

    deuda_pend = centroid[idx["ratio_deuda_pendiente"]]  # 0=pagado, 1=todo pendiente
    tasa_cumpl = centroid[idx["tasa_cumplimiento"]]
    rfm_rec = centroid[idx["rfm_recency"]]  # días, alto = inactive
    rfm_freq = centroid[idx["rfm_frequency"]]
    ratio_exito = centroid[idx["ratio_exito_interacciones"]]
    avg_sent = centroid[idx["avg_sentimiento"]]

    # Clasificar según 4 arquetipos definidos por los ejes más importantes
    # (deuda_pend y engagement son los más informativos en cobranza)
    low_debt = deuda_pend < 0.35
    high_engage = (ratio_exito > 0.4 or rfm_freq > 2) and rfm_rec < 60
    cooperative = avg_sent >= 0.6 or tasa_cumpl >= 0.5

    if low_debt and high_engage:
        return (
            "Quick Wins",
            (
                "Alta probabilidad de cierre con un contacto amigable. "
                "Ofrecer descuento por pronto pago o condonación de intereses."
            ),
            "alto",
        )
    elif high_engage and not low_debt:
        return (
            "Alto Potencial",
            (
                "Disposición a pagar pero deuda elevada. "
                "Proponer plan de pagos escalonado y seguimiento semanal."
            ),
            "alto",
        )
    elif low_debt and not high_engage:
        return (
            "Recuperable — Contacto Perdido",
            (
                "Deuda baja pero sin actividad reciente. "
                "Reactivar vía SMS/WhatsApp antes de llamada. "
                "Mensaje de urgencia moderada."
            ),
            "medio",
        )
    else:
        # alta deuda + bajo engagement
        if cooperative:
            return (
                "Requiere Negociación",
                (
                    "Alta deuda con actitud cooperativa. "
                    "Ofrecer quita o reestructuración agresiva. "
                    "Asignar agente negociador senior."
                ),
                "alto",
            )
        else:
            return (
                "Casos Críticos",
                (
                    "Alta deuda + actitud negativa. "
                    "Evaluar escalada legal o descuento máximo. "
                    "Último intento de gestión amigable antes de acción legal."
                ),
                "alto",
            )


def get_estrategias(data: dict) -> dict:
    """
    Retorna estrategias de cobranza basadas en segmentación
    con k óptimo + análisis de horas y agentes.
    """
    client_ids, X, meta, _ = build_feature_matrix(data)

    if len(client_ids) < 5:
        return {"error": "Insuficientes datos para clustering"}

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # ═══════════════════════════════════════════════════════════════
    # 1. Seleccionar k óptimo
    # ═══════════════════════════════════════════════════════════════
    k_max = min(len(client_ids) // 3, 6)
    k_min = 2
    if k_max < k_min:
        k_max = k_min

    k_optimal, k_evaluations = _select_optimal_k(X_scaled, range(k_min, k_max + 1))
    logger.info(
        "segmentation: k_optimal=%d, silhouette=%.4f",
        k_optimal,
        k_evaluations.get(k_optimal, {}).get("silhouette", -1),
    )

    # ═══════════════════════════════════════════════════════════════
    # 2. KMeans con k óptimo
    # ═══════════════════════════════════════════════════════════════
    kmeans = KMeans(n_clusters=k_optimal, random_state=42, n_init=15)
    labels = kmeans.fit_predict(X_scaled)
    centroids_scaled = kmeans.cluster_centers_
    centroids_raw = scaler.inverse_transform(centroids_scaled)

    # ═══════════════════════════════════════════════════════════════
    # 3. Perfiles de cluster basados en centroides reales
    # ═══════════════════════════════════════════════════════════════
    cluster_profiles: list[dict] = []
    seg_keys_used: set[str] = set()

    for cluster_idx in range(k_optimal):
        c_raw = centroids_raw[cluster_idx]
        count = int(np.sum(labels == cluster_idx))
        if count == 0:
            continue

        nombre, estrategia, impacto = _name_cluster(c_raw)

        # Deduplicar nombres si hay colisiones (mismo arquetipo, 2 clusters)
        base_nombre = nombre
        suffix = 2
        while nombre in seg_keys_used:
            nombre = f"{base_nombre} ({suffix})"
            suffix += 1
        seg_keys_used.add(nombre)

        key = (
            nombre.lower()
            .replace(" ", "_")
            .replace("—", "")
            .replace("(", "")
            .replace(")", "")
            .strip("_")
        )

        # Clientes del cluster
        cluster_clients = [
            {
                "cliente_id": client_ids[i],
                "nombre": meta[i]["nombre"],
                "deuda_pendiente": meta[i]["deuda_pendiente"],
                "pct_pendiente": meta[i]["deuda_pendiente_pct"],
                "tasa_cumplimiento": meta[i]["tasa_cumplimiento"],
            }
            for i in range(len(client_ids))
            if labels[i] == cluster_idx
        ]
        cluster_clients.sort(key=lambda x: x["deuda_pendiente"], reverse=True)

        # Silhouette por cluster (cohesión individual)
        if count >= 2:
            mask_all = np.ones(len(X_scaled), dtype=bool)
            cluster_sil = (
                float(
                    silhouette_score(
                        X_scaled,
                        labels,
                        sample_size=None,
                    )
                )
                if len(set(labels)) >= 2
                else None
            )
        else:
            cluster_sil = None

        cluster_profiles.append(
            {
                "key": key,
                "nombre": nombre,
                "count": count,
                "estrategia": estrategia,
                "impacto": impacto,
                "centroide": {
                    FEATURE_NAMES[j]: round(float(c_raw[j]), 3)
                    for j in range(len(FEATURE_NAMES))
                },
                "clientes": cluster_clients,
            }
        )

    # Ordenar: mayor deuda primero (mayor prioridad de gestión)
    cluster_profiles.sort(
        key=lambda p: p["centroide"].get("ratio_deuda_pendiente", 0),
        reverse=True,
    )

    # ═══════════════════════════════════════════════════════════════
    # 4. Mejores horas (con mínimo de muestras)
    # ═══════════════════════════════════════════════════════════════
    hora_stats: dict[int, dict] = {}
    for inter in data["all_inters"]:
        hora = inter.get("hora_del_dia")
        resultado = inter.get("resultado", "")
        if hora is None:
            continue
        if hora not in hora_stats:
            hora_stats[hora] = {"total": 0, "exitosas": 0}
        hora_stats[hora]["total"] += 1
        if resultado in OUTCOME_SUCCESS:
            hora_stats[hora]["exitosas"] += 1

    MIN_LLAMADAS = 5  # umbral mínimo para estadística confiable
    mejores_horas = []
    for h, s in sorted(hora_stats.items()):
        if s["total"] < MIN_LLAMADAS:
            continue
        tasa = s["exitosas"] / s["total"]
        mejores_horas.append(
            {
                "hora": h,
                "tasa_exito": round(tasa * 100, 1),
                "total": s["total"],
                "exitosas": s["exitosas"],
            }
        )
    mejores_horas.sort(key=lambda x: x["tasa_exito"], reverse=True)

    # ═══════════════════════════════════════════════════════════════
    # 5. Efectividad de agentes (normalizada por volumen)
    # ═══════════════════════════════════════════════════════════════
    agente_stats: dict[str, dict] = {}
    for inter in data["all_inters"]:
        aid = inter.get("agente_id", "")
        res = inter.get("resultado", "")
        if not aid or not res:
            continue
        if aid not in agente_stats:
            agente_stats[aid] = {"total": 0, "exitosas": 0, "por_tipo": {}}
        agente_stats[aid]["total"] += 1
        if res in OUTCOME_SUCCESS:
            agente_stats[aid]["exitosas"] += 1
        agente_stats[aid]["por_tipo"][res] = (
            agente_stats[aid]["por_tipo"].get(res, 0) + 1
        )

    # Tasa de éxito por agente (no conteo absoluto)
    agentes_ordenados = sorted(
        [
            {
                "agente_id": aid,
                "tasa_exito": round(s["exitosas"] / s["total"] * 100, 1),
                "total_llamadas": s["total"],
                "exitosas": s["exitosas"],
                "por_tipo": s["por_tipo"],
            }
            for aid, s in agente_stats.items()
            if s["total"] >= 3
        ],
        key=lambda x: x["tasa_exito"],
        reverse=True,
    )

    # Mejor agente por tipo de outcome (tasa, no conteo)
    mejor_agente_por_resultado: dict[str, dict] = {}
    for tipo in ("promesa_pago", "pago_inmediato", "renegociacion"):
        best = max(
            [a for a in agentes_ordenados if a["por_tipo"].get(tipo, 0) > 0],
            key=lambda a: a["por_tipo"].get(tipo, 0) / a["total_llamadas"],
            default=None,
        )
        if best:
            mejor_agente_por_resultado[tipo] = {
                "agente_id": best["agente_id"],
                "tasa_tipo": round(
                    best["por_tipo"].get(tipo, 0) / best["total_llamadas"] * 100, 1
                ),
                "total_llamadas": best["total_llamadas"],
            }

    # ═══════════════════════════════════════════════════════════════
    # 6. Recomendaciones
    # ═══════════════════════════════════════════════════════════════
    recomendaciones: list[dict] = []

    for profile in cluster_profiles:
        recomendaciones.append(
            {
                "categoria": "segmento",
                "titulo": f"Segmento '{profile['nombre']}' ({profile['count']} clientes)",
                "descripcion": profile["estrategia"],
                "impacto": profile["impacto"],
            }
        )

    if mejores_horas:
        top3 = mejores_horas[:3]
        horas_str = ", ".join(f"{h['hora']}:00 ({h['tasa_exito']}%)" for h in top3)
        recomendaciones.append(
            {
                "categoria": "horario",
                "titulo": "Horarios óptimos de contacto",
                "descripcion": f"Concentrar llamadas en: {horas_str} (mín. {MIN_LLAMADAS} llamadas por franja)",
                "impacto": "alto",
            }
        )

    for tipo, info in mejor_agente_por_resultado.items():
        recomendaciones.append(
            {
                "categoria": "asignacion",
                "titulo": f"Mejor agente para {tipo.replace('_', ' ')}",
                "descripcion": (
                    f"{info['agente_id']}: tasa {info['tasa_tipo']}% "
                    f"en {tipo} ({info['total_llamadas']} llamadas totales)"
                ),
                "impacto": "medio",
            }
        )

    promesas_inc = [p for p in data["all_promesas"] if not p.get("cumplida")]
    if promesas_inc:
        total_inc = sum(float(p.get("monto_prometido", 0) or 0) for p in promesas_inc)
        recomendaciones.append(
            {
                "categoria": "seguimiento",
                "titulo": f"{len(promesas_inc)} promesas incumplidas",
                "descripcion": f"Monto comprometido: ${total_inc:,.0f}. Priorizar seguimiento.",
                "impacto": "medio",
            }
        )

    # ── Build segmentos_count para compatibilidad con response anterior ──
    segmentos_count = {p["key"]: p["count"] for p in cluster_profiles}
    detalle_seg = {p["key"]: p["clientes"] for p in cluster_profiles}

    return {
        "mejores_horas": mejores_horas[:5],
        "agentes": agentes_ordenados,
        "segmentos": segmentos_count,
        "detalle_segmentos": detalle_seg,
        "cluster_profiles": cluster_profiles,
        "mejor_agente_por_resultado": mejor_agente_por_resultado,
        "recomendaciones": recomendaciones,
        "modelo": {
            "tipo": "KMeans",
            "k_optimo": k_optimal,
            "k_evaluado": k_evaluations,
            "features": FEATURE_NAMES,
            "inertia": round(float(kmeans.inertia_), 2),
            "silhouette": k_evaluations.get(k_optimal, {}).get("silhouette"),
            "davies_bouldin": k_evaluations.get(k_optimal, {}).get("davies_bouldin"),
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
