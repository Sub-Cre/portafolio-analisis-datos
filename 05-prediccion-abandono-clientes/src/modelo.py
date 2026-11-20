"""Modelo de predicción de abandono de clientes (churn).

1. Análisis exploratorio: tasa de abandono por tipo de contrato, método de pago, etc.
2. Entrena y compara Regresión Logística vs Random Forest (validación cruzada de 5 pliegues + test 25%).
3. Explica el modelo con importancia por permutación (en qué variables se apoya).
4. Traduce el resultado a negocio: cuántos clientes que se van detecta si contactamos al 20% más riesgoso.

Salidas en outputs/: dashboard_churn.png, metricas.json, clientes_alto_riesgo.csv
"""
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, roc_curve
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from estilo import GRAY, MUTED, S1, S2, SURF, TXT2, header, hbar_labels, kpi_row

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "outputs"
SEED = 42

CATEGORICAS = ["region", "tipo_contrato", "plan", "metodo_pago"]
NUMERICAS = ["antiguedad_meses", "cargo_mensual", "tickets_soporte_90d", "pagos_atrasados_12m", "usa_app"]
NOMBRES = {"antiguedad_meses": "Antigüedad", "cargo_mensual": "Cargo mensual", "tickets_soporte_90d": "Tickets de soporte",
           "pagos_atrasados_12m": "Pagos atrasados", "usa_app": "Usa la app", "region": "Región",
           "tipo_contrato": "Tipo de contrato", "plan": "Plan", "metodo_pago": "Método de pago"}


def preprocesador():
    return ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAS),
        ("num", StandardScaler(), NUMERICAS),
    ])


def modelos():
    return {
        "Regresión logística": Pipeline([("prep", preprocesador()), ("clf", LogisticRegression(max_iter=2000))]),
        "Random Forest": Pipeline([("prep", preprocesador()),
                                   ("clf", RandomForestClassifier(n_estimators=400, min_samples_leaf=10,
                                                                  random_state=SEED, n_jobs=-1))]),
    }


def captura_top(y_true, prob, frac=0.20):
    """% de los que abandonan que están dentro del `frac` de clientes con mayor probabilidad."""
    orden = np.argsort(-prob)
    k = int(len(prob) * frac)
    return y_true[orden[:k]].sum() / y_true.sum()


def main():
    OUT.mkdir(exist_ok=True)
    df = pd.read_csv(BASE / "data" / "clientes_suscripcion.csv")
    X, y = df[CATEGORICAS + NUMERICAS], df.abandono.values
    X_tr, X_te, y_tr, y_te, id_tr, id_te = train_test_split(X, y, df.id_cliente, test_size=0.25,
                                                            stratify=y, random_state=SEED)

    cv = StratifiedKFold(5, shuffle=True, random_state=SEED)
    resultados = {}
    for nombre, pipe in modelos().items():
        cv_auc = cross_val_score(pipe, X_tr, y_tr, cv=cv, scoring="roc_auc")
        pipe.fit(X_tr, y_tr)
        prob = pipe.predict_proba(X_te)[:, 1]
        resultados[nombre] = {"pipe": pipe, "prob": prob, "cv_auc": cv_auc.mean(), "cv_std": cv_auc.std(),
                              "test_auc": roc_auc_score(y_te, prob), "captura20": captura_top(y_te, prob)}
        print(f"{nombre}: AUC CV {cv_auc.mean():.3f} ± {cv_auc.std():.3f} | AUC test {resultados[nombre]['test_auc']:.3f}")

    mejor = max(resultados, key=lambda k: resultados[k]["cv_auc"])
    r = resultados[mejor]
    imp = permutation_importance(r["pipe"], X_te, y_te, scoring="roc_auc", n_repeats=10, random_state=SEED)
    importancia = pd.Series(imp.importances_mean, index=[NOMBRES[c] for c in X_te.columns]).sort_values()

    # lista accionable para el equipo de retención
    riesgo = pd.DataFrame({"id_cliente": id_te.values, "probabilidad_abandono": r["prob"].round(3)})
    riesgo["nivel"] = pd.cut(riesgo.probabilidad_abandono, [0, 0.3, 0.6, 1], labels=["Bajo", "Medio", "Alto"],
                             include_lowest=True)
    riesgo.sort_values("probabilidad_abandono", ascending=False).query("nivel == 'Alto'") \
          .to_csv(OUT / "clientes_alto_riesgo.csv", index=False)

    por_contrato = df.groupby("tipo_contrato").abandono.mean().mul(100).reindex(["Mensual", "Anual", "Bianual"])
    por_pago = df.groupby("metodo_pago").abandono.mean().mul(100)
    app = df.groupby("usa_app").abandono.mean().mul(100)

    m = {
        "clientes": int(len(df)),
        "tasa_abandono_pct": round(df.abandono.mean() * 100, 1),
        "modelo_elegido": mejor,
        "modelos": {k: {"auc_cv": round(v["cv_auc"], 3), "auc_cv_std": round(v["cv_std"], 3),
                        "auc_test": round(v["test_auc"], 3), "captura_top20_pct": round(v["captura20"] * 100, 1)}
                    for k, v in resultados.items()},
        "abandono_por_contrato_pct": por_contrato.round(1).to_dict(),
        "abandono_por_pago_pct": por_pago.round(1).to_dict(),
        "abandono_usa_app_pct": round(float(app[1]), 1),
        "abandono_no_usa_app_pct": round(float(app[0]), 1),
        "top_factores": importancia.sort_values(ascending=False).head(5).round(4).to_dict(),
        "clientes_alto_riesgo_test": int((riesgo.nivel == "Alto").sum()),
        "clientes_test": int(len(riesgo)),
    }
    (OUT / "metricas.json").write_text(json.dumps(m, indent=2, ensure_ascii=False), encoding="utf-8")

    fig = plt.figure(figsize=(16, 10), dpi=110)
    header(fig, "Predicción de Abandono de Clientes (Churn)",
           "Servicio por suscripción, 7.000 clientes. Python + scikit-learn: comparación de modelos, explicación y uso en negocio.")
    kpi_row(fig, [("Tasa de abandono", f"{m['tasa_abandono_pct']:.0f}%", None),
                  ("AUC del modelo", f"{r['test_auc']:.2f}", mejor),
                  ("Detectados en el top 20%", f"{r['captura20'] * 100:.0f}%", "de los que se van"),
                  ("Clientes en riesgo alto", f"{m['clientes_alto_riesgo_test']}", f"de {len(riesgo):,} en test".replace(",", "."))])

    ax = fig.add_axes([0.035, 0.42, 0.28, 0.29])
    ax.bar(por_contrato.index, por_contrato.values, color=[S2, GRAY, GRAY], width=0.55)
    for i, v in enumerate(por_contrato.values):
        ax.text(i, v + 1, f"{v:.0f}%", ha="center", fontsize=10.5)
    ax.set_ylim(0, por_contrato.max() * 1.2)
    ax.set_title("Abandono por tipo de contrato")

    ax = fig.add_axes([0.37, 0.42, 0.27, 0.29])
    for (nombre, v), col in zip(resultados.items(), [S1, S2]):
        fpr, tpr, _ = roc_curve(y_te, v["prob"])
        ax.plot(fpr, tpr, color=col, lw=2, label=f"{nombre} (AUC {v['test_auc']:.2f})")
    ax.plot([0, 1], [0, 1], color=MUTED, lw=1, ls="--", label="Al azar")
    ax.set_xlabel("Falsos positivos")
    ax.set_ylabel("Verdaderos positivos")
    ax.grid(axis="both")
    ax.legend(frameon=False, fontsize=9.5, loc="lower right")
    ax.set_title("Curva ROC en datos de prueba")

    ax = fig.add_axes([0.80, 0.42, 0.165, 0.29])
    top = importancia.tail(6)
    ax.barh(top.index, top.values, color=S1, height=0.6)
    hbar_labels(ax, top.values, lambda v: "")
    ax.set_xticks([])
    ax.set_title("Qué más pesa en la predicción")

    ax = fig.add_axes([0.035, 0.06, 0.45, 0.28])
    orden = np.argsort(-r["prob"])
    acum = np.cumsum(y_te[orden]) / y_te.sum()
    pct = np.arange(1, len(acum) + 1) / len(acum)
    ax.plot(pct * 100, acum * 100, color=S1, lw=2.2, label=f"Con el modelo ({mejor})")
    ax.plot([0, 100], [0, 100], color=MUTED, lw=1, ls="--", label="Contactando al azar")
    ax.axvline(20, color=GRAY, lw=1)
    ax.annotate(f"Contactando al 20% más riesgoso\nse detecta el {r['captura20'] * 100:.0f}% de los que se van",
                xy=(20, r["captura20"] * 100), xytext=(30, 25), fontsize=10.5, color=TXT2,
                arrowprops=dict(arrowstyle="-", color=MUTED))
    ax.set_xlabel("% de clientes contactados (de mayor a menor riesgo)")
    ax.set_ylabel("% de abandonos detectados")
    ax.grid(axis="both")
    ax.legend(frameon=False, loc="lower right", fontsize=10)
    ax.set_title("Curva de ganancia acumulada")

    ax = fig.add_axes([0.53, 0.06, 0.435, 0.28])
    from estilo import panel_texto
    pc = por_contrato
    panel_texto(ax, "Recomendaciones para el equipo de retención", (
        f"1. El contrato mensual abandona {pc['Mensual'] / pc['Bianual']:.0f} veces más que el bianual\n"
        f"    ({pc['Mensual']:.0f}% vs {pc['Bianual']:.0f}%): ofrecer migración a plan anual con descuento.\n\n"
        f"2. Quien no usa la app abandona más ({m['abandono_no_usa_app_pct']:.0f}% vs {m['abandono_usa_app_pct']:.0f}%):\n"
        "    campaña de activación de la app en el primer mes.\n\n"
        "3. Pagos atrasados y tickets de soporte son señales tempranas:\n"
        "    llamar al cliente después del 2.º ticket.\n\n"
        f"4. Usar el modelo cada mes y contactar primero a los {m['clientes_alto_riesgo_test']} de riesgo alto."), size=11)
    fig.savefig(OUT / "dashboard_churn.png", facecolor=SURF)
    plt.close(fig)
    print(json.dumps(m, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
