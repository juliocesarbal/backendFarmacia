"""
Servicio de analitica: segmentacion de productos con K-means.

Construye un dataset por producto (consumo, costo, stock, n compras, rotacion)
con consultas agregadas (sin N+1), normaliza y aplica KMeans (scikit-learn).
La interpretacion de cada cluster se deriva de sus centroides reales, no del
numero de cluster (que KMeans asigna al azar). Modulo complementario.
"""
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Count, Q, Sum
from django.utils import timezone

from apps.catalogos.models import Producto
from apps.inventario.models import CapaCosto, MovimientoInventario

from .models import ClusterKMeans, EjecucionKMeans, ProductoCluster


def _construir_dataset(periodo_inicio, periodo_fin):
    """Devuelve (filas, meta) en pocas consultas agregadas (no por producto)."""
    productos = list(
        Producto.objects.filter(estado="ACTIVO").only("id", "codigo_producto", "nombre")
    )

    # Rango por datetime con zona horaria (NO __date) para usar el indice de fecha
    inicio_dt = timezone.make_aware(datetime.combine(periodo_inicio, time.min))
    fin_dt = timezone.make_aware(datetime.combine(periodo_fin + timedelta(days=1), time.min))

    # UNA sola pasada sobre movimiento_inventario: consumo/costo (salidas) y
    # nro de compras por producto, con agregacion condicional.
    movs = (
        MovimientoInventario.objects.filter(
            fecha_movimiento__gte=inicio_dt,
            fecha_movimiento__lt=fin_dt,
        )
        .values("producto_id")
        .annotate(
            consumo=Sum("cantidad", filter=Q(sentido="SALIDA")),
            costo=Sum("valor_movimiento", filter=Q(sentido="SALIDA")),
            n_compras=Count("id", filter=Q(tipo_movimiento="COMPRA")),
        )
    )
    mov_map = {r["producto_id"]: r for r in movs}

    # Stock actual = suma de capas activas por producto
    stock = (
        CapaCosto.objects.filter(estado="ACTIVA")
        .values("producto_id")
        .annotate(s=Sum("cantidad_disponible"))
    )
    stock_map = {r["producto_id"]: r["s"] for r in stock}

    filas, meta = [], []
    for p in productos:
        m = mov_map.get(p.id, {})
        consumo = m.get("consumo") or Decimal("0")
        costo = m.get("costo") or Decimal("0")
        n_compras = m.get("n_compras") or 0
        stock_val = stock_map.get(p.id) or Decimal("0")
        rotacion = float(consumo) / float(stock_val) if stock_val else 0.0
        filas.append(
            [float(consumo), float(costo), float(stock_val), float(n_compras), rotacion]
        )
        meta.append(
            {
                "producto": p,
                "consumo": consumo,
                "costo": costo,
                "stock": stock_val,
                "rotacion": Decimal(str(round(rotacion, 4))),
            }
        )
    return filas, meta


def _interpretar(filas, etiquetas, k):
    """Asigna una etiqueta a cada cluster segun su centroide real (z-score vs
    la media global). Columnas: [consumo, costo, stock, n_compras, rotacion]."""
    import numpy as np

    X = np.array(filas, dtype=float)
    glob = X.mean(axis=0)
    std = X.std(axis=0) + 1e-9
    etiquetas = np.array(etiquetas)
    res = {}
    for c in range(k):
        mask = etiquetas == c
        if not mask.any():
            res[c] = "Sin productos"
            continue
        z = (X[mask].mean(axis=0) - glob) / std
        consumo_z, costo_z, stock_z, _compras_z, rot_z = z
        if rot_z > 0.5 and consumo_z > 0:
            res[c] = "Alta rotacion"
        elif stock_z > 0.5 and rot_z < 0:
            res[c] = "Riesgo de sobrestock"
        elif costo_z > 0.5:
            res[c] = "Alto costo / valor consumido"
        elif consumo_z < -0.2 and rot_z <= 0:
            res[c] = "Baja rotacion / bajo movimiento"
        else:
            res[c] = "Comportamiento medio"
    return res


@transaction.atomic
def ejecutar_kmeans(k, periodo_inicio, periodo_fin, usuario=None):
    import numpy as np
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler

    filas, meta = _construir_dataset(periodo_inicio, periodo_fin)
    ejecucion = EjecucionKMeans.objects.create(
        numero_clusters=k,
        periodo_inicio=periodo_inicio,
        periodo_fin=periodo_fin,
        variables_usadas=["consumo", "costo", "stock", "n_compras", "rotacion"],
        usuario=usuario,
    )

    if len(filas) < k:
        cluster = ClusterKMeans.objects.create(
            ejecucion=ejecucion,
            numero_cluster=0,
            nombre_cluster="General",
            descripcion="Datos insuficientes para segmentar",
        )
        ProductoCluster.objects.bulk_create(
            [
                ProductoCluster(
                    cluster=cluster, producto=m["producto"], rotacion=m["rotacion"],
                    consumo_total=m["consumo"], costo_total=m["costo"],
                    stock_actual=m["stock"],
                )
                for m in meta
            ]
        )
        return ejecucion

    X = StandardScaler().fit_transform(np.array(filas))
    modelo = KMeans(n_clusters=k, random_state=42, n_init=10)
    etiquetas = modelo.fit_predict(X)

    # Interpretacion derivada de los centroides reales
    desc = _interpretar(filas, etiquetas, k)
    clusters = {
        c: ClusterKMeans.objects.create(
            ejecucion=ejecucion,
            numero_cluster=c,
            nombre_cluster=f"Cluster {c}",
            descripcion=desc.get(c, "Sin interpretacion"),
        )
        for c in range(k)
    }

    ProductoCluster.objects.bulk_create(
        [
            ProductoCluster(
                cluster=clusters[int(etiqueta)], producto=m["producto"],
                rotacion=m["rotacion"], consumo_total=m["consumo"],
                costo_total=m["costo"], stock_actual=m["stock"],
            )
            for etiqueta, m in zip(etiquetas, meta)
        ]
    )
    return ejecucion
