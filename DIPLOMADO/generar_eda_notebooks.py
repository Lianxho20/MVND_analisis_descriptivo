# -*- coding: utf-8 -*-
"""Genera notebooks 03-07 del EDA completo."""
import json
from pathlib import Path

OUT = Path(__file__).parent

SETUP_CODE = r'''
import sys
EN_COLAB = 'google.colab' in sys.modules
RUTA_LIMPIO = 'mvnd_limpio.csv'
print('Entorno:', 'Google Colab' if EN_COLAB else 'Jupyter Local')
'''.strip()

IMPORTS_CODE = r'''
!pip install pandas matplotlib seaborn scipy openpyxl --quiet

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

plt.rcParams['figure.figsize'] = (12, 5)
plt.rcParams['font.size'] = 10
sns.set_theme(style='whitegrid', palette='muted')

CARPETA_GRAFICOS = 'graficos_eda'
import os
os.makedirs(CARPETA_GRAFICOS, exist_ok=True)

def guardar(fig, nombre):
    ruta = os.path.join(CARPETA_GRAFICOS, nombre)
    fig.savefig(ruta, dpi=150, bbox_inches='tight')
    print(f'💾 Guardado: {ruta}')
'''.strip()

LOAD_CODE = r'''
df = pd.read_csv(RUTA_LIMPIO, encoding='utf-8-sig')
df['FECHA_AUTORIZACION'] = pd.to_datetime(df['FECHA_AUTORIZACION'])

# Corregir nombre de columna año parcial (encoding en CSV)
for c in list(df.columns):
    if 'PARCIAL' in c.upper():
        df = df.rename(columns={c: 'ANIO_PARCIAL'})

print(f'✅ Dataset cargado: {len(df):,} registros × {df.shape[1]} columnas')
print(f'   Período: {df["FECHA_AUTORIZACION"].min().date()} → {df["FECHA_AUTORIZACION"].max().date()}')
'''.strip()


def md(text):
    return {"cell_type": "markdown", "metadata": {}, "source": [line + "\n" for line in text.split("\n")]}


def code(text):
    return {"cell_type": "code", "metadata": {}, "source": [line + "\n" for line in text.split("\n")], "outputs": [], "execution_count": None}


def notebook(cells):
    return {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.10.0"},
        },
        "cells": cells,
    }


def save(name, cells):
    path = OUT / name
    with open(path, "w", encoding="utf-8") as f:
        json.dump(notebook(cells), f, ensure_ascii=False, indent=1)
    print("Creado:", path.name)


# ─── 03 MEDICAMENTOS ───────────────────────────────────────────────────────────
save("03_EDA_Medicamentos.ipynb", [
    md("""# 💊 Sprint 1 — EDA: Medicamentos
## Medicamentos Vitales No Disponibles — INVIMA (2018–2026)

**Proyecto:** Entre la necesidad y la disponibilidad  
**Autores:** Julian David Medina Ceballos | Laura Catalina Mariaca Varona  
**Insumo:** `mvnd_limpio.csv`

### Objetivos del sprint
- Identificar principios activos con mayor demanda
- Analizar formas farmacéuticas y medicamentos combinados
- Caracterizar volúmenes solicitados (`CANTIDAD`)"""),
    md("## ⚙️ Configuración"),
    code(SETUP_CODE),
    code(IMPORTS_CODE),
    code(LOAD_CODE),
    md("## 1. Concentración de la demanda por principio activo"),
    code("""
TOP_N = 20
top_activos = df['PRINCIPIO_ACTIVO'].value_counts().head(TOP_N)
total = len(df)
top3_pct = top_activos.head(3).sum() / total * 100
top10_pct = top_activos.head(10).sum() / total * 100

fig, ax = plt.subplots(figsize=(13, 8))
colores = ['#c00000' if i < 3 else '#4472C4' for i in range(len(top_activos))]
bars = ax.barh(top_activos.index[::-1], top_activos.values[::-1], color=colores[::-1])
for bar, val in zip(bars, top_activos.values[::-1]):
    ax.text(bar.get_width() + 8, bar.get_y() + bar.get_height()/2, f'{val:,}', va='center', fontsize=9)
ax.set_title('Top 20 principios activos — Autorizaciones MVND 2018–2026', fontsize=13)
ax.set_xlabel('Número de autorizaciones')
ax.axvline(top_activos.mean(), color='orange', linestyle='--', label=f'Media top 20: {top_activos.mean():.0f}')
ax.legend()
plt.tight_layout()
guardar(plt.gcf(), '03_top20_principios_activos.png')
plt.show()

print(f'Principios activos únicos: {df["PRINCIPIO_ACTIVO"].nunique():,}')
print(f'Top 3 concentran: {top3_pct:.1f}% | Top 10: {top10_pct:.1f}%')
display(top_activos.reset_index().rename(columns={'index':'Principio activo', 'PRINCIPIO_ACTIVO':'Autorizaciones'}))
"""),
    md("## 2. Curva de Pareto (concentración)"),
    code("""
vc = df['PRINCIPIO_ACTIVO'].value_counts()
cum = vc.cumsum() / vc.sum() * 100
n_80 = (cum <= 80).sum() + 1

fig, ax1 = plt.subplots(figsize=(12, 5))
ax1.bar(range(min(30, len(vc))), vc.head(30).values, color='#4472C4', alpha=0.8)
ax1.set_ylabel('Autorizaciones')
ax1.set_xlabel('Ranking principio activo')
ax1.set_title('Pareto — Top 30 principios activos')

ax2 = ax1.twinx()
ax2.plot(range(min(30, len(cum))), cum.head(30).values, color='#c00000', marker='o', linewidth=2)
ax2.axhline(80, color='gray', linestyle='--', alpha=0.7)
ax2.set_ylabel('% acumulado')
ax2.set_ylim(0, 105)
plt.tight_layout()
guardar(plt.gcf(), '03_pareto_principios_activos.png')
plt.show()
print(f'≈ {n_80} principios activos explican el 80% de las autorizaciones')
"""),
    md("## 3. Formas farmacéuticas"),
    code("""
top_formas = df['FORMA_FARMACEUTICA'].value_counts().head(12)
fig, ax = plt.subplots(figsize=(11, 5))
ax.bar(top_formas.index, top_formas.values, color='#70AD47')
for i, v in enumerate(top_formas.values):
    ax.text(i, v + 15, f'{v:,}', ha='center', fontsize=9)
ax.set_title('Top 12 formas farmacéuticas')
ax.set_ylabel('Autorizaciones')
plt.xticks(rotation=35, ha='right')
plt.tight_layout()
guardar(plt.gcf(), '03_formas_farmaceuticas.png')
plt.show()
"""),
    md("## 4. Medicamentos combinados (`ES_COMBINADO`)"),
    code("""
comb = df['ES_COMBINADO'].value_counts()
fig, axes = plt.subplots(1, 2, figsize=(12, 4))
axes[0].pie(comb.values, labels=['Un principio', 'Combinado (2 P.A.)'],
            autopct='%1.1f%%', colors=['#4472C4', '#ED7D31'], startangle=90)
axes[0].set_title('Proporción medicamentos combinados')
top_comb = df[df['ES_COMBINADO']==1]['PRINCIPIO_ACTIVO'].value_counts().head(10)
axes[1].barh(top_comb.index[::-1], top_comb.values[::-1], color='#ED7D31')
axes[1].set_title('Top 10 combinados')
plt.tight_layout()
guardar(plt.gcf(), '03_medicamentos_combinados.png')
plt.show()
print(comb.rename({0:'Simples', 1:'Combinados'}))
"""),
    md("## 5. Cantidad solicitada por tipo de solicitud"),
    code("""
p99 = df['CANTIDAD'].quantile(0.99)
df_c = df[df['CANTIDAD'] <= p99].copy()

fig, axes = plt.subplots(1, 2, figsize=(14, 5))
orden = ['PACIENTE ESPECIFICO', 'MAS DE UN PACIENTE', 'URGENCIA CLINICA']
sns.boxplot(data=df_c, x='TIPO_SOLICITUD', y='CANTIDAD', order=orden, ax=axes[0], palette='Set2')
axes[0].set_title(f'Cantidad por tipo de solicitud (≤ P99 = {p99:.0f})')
axes[0].tick_params(axis='x', rotation=15)

stats = df.groupby('TIPO_SOLICITUD')['CANTIDAD'].agg(['count','median','mean']).reindex(orden)
stats.plot(kind='bar', ax=axes[1], color=['#4472C4','#ED7D31','#c00000'])
axes[1].set_title('Media vs mediana de cantidad')
axes[1].tick_params(axis='x', rotation=15)
axes[1].legend(['N','Mediana','Media'])
plt.tight_layout()
guardar(plt.gcf(), '03_cantidad_por_tipo.png')
plt.show()
print(stats.round(1))
"""),
    md("## 6. Categorías de cantidad"),
    code("""
cat = df['CANTIDAD_CATEGORIA'].value_counts().sort_index()
fig, ax = plt.subplots(figsize=(10, 4))
cat.plot(kind='barh', ax=ax, color='#5B9BD5')
ax.set_title('Distribución por categoría de cantidad solicitada')
plt.tight_layout()
guardar(plt.gcf(), '03_cantidad_categoria.png')
plt.show()
"""),
    md("""## 📋 Hallazgos — Sprint 1 (Medicamentos)

| Hallazgo | Evidencia |
|----------|-----------|
| Alta concentración | Top 3 principios activos (fibrosis quística, distrofia muscular, Bardet-Biedl) dominan la demanda |
| Cola larga | Cientos de principios activos con pocas autorizaciones cada uno |
| Formas | Soluciones, tabletas y polvos liofilizados son las más frecuentes |
| Combinados | ~8% de registros corresponden a 2 principios activos |
| Cantidad | Distribución muy sesgada; urgencias y solicitudes masivas elevan la media |

**Siguiente:** `04_EDA_Diagnosticos.ipynb`"""),
])

# ─── 04 DIAGNÓSTICOS ─────────────────────────────────────────────────────────
save("04_EDA_Diagnosticos.ipynb", [
    md("""# 🩺 Sprint 2 — EDA: Diagnósticos CIE-10
**Insumo:** `mvnd_limpio.csv`

### Objetivos
- Perfil diagnóstico de las autorizaciones con CIE-10 reportado
- Distribución por capítulo CIE-10
- Relación medicamento ↔ diagnóstico"""),
    md("## ⚙️ Configuración"),
    code(SETUP_CODE),
    code(IMPORTS_CODE),
    code(LOAD_CODE),
    md("## 1. Cobertura diagnóstica"),
    code("""
sin_dx = df['DIAGNOSTICO'].isna().sum()
con_dx = len(df) - sin_dx
pct_sin = sin_dx / len(df) * 100

fig, ax = plt.subplots(figsize=(6, 4))
ax.bar(['Con diagnóstico', 'Sin diagnóstico'], [con_dx, sin_dx], color=['#70AD47', '#d62728'])
for i, v in enumerate([con_dx, sin_dx]):
    ax.text(i, v + 50, f'{v:,}\\n({v/len(df)*100:.1f}%)', ha='center')
ax.set_title('Cobertura del campo diagnóstico')
ax.set_ylabel('Registros')
plt.tight_layout()
guardar(plt.gcf(), '04_cobertura_diagnostico.png')
plt.show()

df_dx = df[df['DIAGNOSTICO'].notna()].copy()
print(f'Análisis con diagnóstico: {len(df_dx):,} registros ({100-pct_sin:.1f}%)')
"""),
    md("## 2. Top diagnósticos textuales"),
    code("""
top_dx = df_dx['DIAGNOSTICO'].value_counts().head(15)
fig, ax = plt.subplots(figsize=(13, 7))
ax.barh(top_dx.index[::-1], top_dx.values[::-1], color='#70AD47')
for bar, val in zip(ax.patches, top_dx.values[::-1]):
    ax.text(val + 5, bar.get_y() + bar.get_height()/2, f'{val:,}', va='center', fontsize=9)
ax.set_title('Top 15 diagnósticos (excluye NO REPORTADO)')
ax.set_xlabel('Autorizaciones')
plt.tight_layout()
guardar(plt.gcf(), '04_top15_diagnosticos.png')
plt.show()
"""),
    md("## 3. Capítulos CIE-10"),
    code("""
cap = df_dx['CAPITULO_CIE10'].value_counts().head(12)
fig, ax = plt.subplots(figsize=(12, 6))
ax.barh(cap.index[::-1], cap.values[::-1], color='#4472C4')
ax.set_title('Autorizaciones por capítulo CIE-10')
ax.set_xlabel('Registros')
plt.tight_layout()
guardar(plt.gcf(), '04_capitulos_cie10.png')
plt.show()
print(cap.head(10))
"""),
    md("## 4. Heatmap: capítulo CIE-10 × tipo de solicitud"),
    code("""
top_cap = df_dx['CAPITULO_CIE10'].value_counts().head(8).index
tab = pd.crosstab(df_dx[df_dx['CAPITULO_CIE10'].isin(top_cap)]['CAPITULO_CIE10'],
                  df_dx[df_dx['CAPITULO_CIE10'].isin(top_cap)]['TIPO_SOLICITUD'])
fig, ax = plt.subplots(figsize=(10, 6))
sns.heatmap(tab, annot=True, fmt='d', cmap='YlGnBu', ax=ax)
ax.set_title('Capítulo CIE-10 vs tipo de solicitud (top 8 capítulos)')
plt.tight_layout()
guardar(plt.gcf(), '04_heatmap_capitulo_tipo.png')
plt.show()
"""),
    md("## 5. Principio activo vs capítulo (top medicamentos)"),
    code("""
top_pa = df_dx['PRINCIPIO_ACTIVO'].value_counts().head(8).index
top_c = df_dx['CAPITULO_CIE10'].value_counts().head(8).index
sub = df_dx[df_dx['PRINCIPIO_ACTIVO'].isin(top_pa) & df_dx['CAPITULO_CIE10'].isin(top_c)]
tab2 = pd.crosstab(sub['PRINCIPIO_ACTIVO'], sub['CAPITULO_CIE10'])
fig, ax = plt.subplots(figsize=(12, 7))
sns.heatmap(tab2, annot=True, fmt='d', cmap='Oranges', ax=ax)
ax.set_title('Top principios activos × capítulos CIE-10')
plt.tight_layout()
guardar(plt.gcf(), '04_heatmap_medicamento_capitulo.png')
plt.show()
"""),
    md("""## 📋 Hallazgos — Sprint 2 (Diagnósticos)

| Hallazgo | Evidencia |
|----------|-----------|
| Datos faltantes | ~13,4% sin diagnóstico — limitar inferencias al subconjunto con CIE-10 |
| Oncología y endocrino | Capítulos C y E concentran gran parte de la demanda con diagnóstico |
| Coherencia clínica | ELEXACAFTOR/TEZACAFTOR/IVACAFTOR se asocia a capítulo respiratorio/endocrino (fibrosis quística) |
| Urgencias | Distribución heterogénea por capítulo en `URGENCIA CLINICA` |

**Siguiente:** `05_EDA_Importadores.ipynb`"""),
])

# ─── 05 IMPORTADORES ─────────────────────────────────────────────────────────
save("05_EDA_Importadores.ipynb", [
    md("""# 🏢 Sprint 3 — EDA: Importadores
**Insumo:** `mvnd_limpio.csv`

### Objetivos
- Medir concentración de autorizaciones por importador
- Identificar actores dominantes (Pareto)
- Relacionar importador ↔ medicamento"""),
    md("## ⚙️ Configuración"),
    code(SETUP_CODE),
    code(IMPORTS_CODE),
    code(LOAD_CODE),
    md("## 1. Top importadores"),
    code("""
n_imp = df['IMPORTADOR'].nunique()
top_imp = df['IMPORTADOR'].value_counts().head(20)
top5_pct = top_imp.head(5).sum() / len(df) * 100
top10_pct = top_imp.head(10).sum() / len(df) * 100

fig, ax = plt.subplots(figsize=(13, 8))
colores = ['#c00000' if i == 0 else '#ED7D31' if i < 3 else '#4472C4' for i in range(len(top_imp))]
ax.barh(top_imp.index[::-1], top_imp.values[::-1], color=colores[::-1])
for bar, val in zip(ax.patches, top_imp.values[::-1]):
    ax.text(val + 10, bar.get_y() + bar.get_height()/2, f'{val:,}', va='center', fontsize=8)
ax.set_title(f'Top 20 importadores — {n_imp} empresas únicas')
ax.set_xlabel('Autorizaciones')
plt.tight_layout()
guardar(plt.gcf(), '05_top20_importadores.png')
plt.show()
print(f'Top 5 concentran: {top5_pct:.1f}% | Top 10: {top10_pct:.1f}%')
"""),
    md("## 2. Curva de concentración (Lorenz / Pareto)"),
    code("""
vc = df['IMPORTADOR'].value_counts().sort_values(ascending=False)
cum = vc.cumsum() / vc.sum() * 100

fig, ax = plt.subplots(figsize=(8, 5))
ax.plot(range(1, len(cum)+1), cum.values, color='#c00000', linewidth=2)
ax.axhline(80, color='gray', linestyle='--', label='80% demanda')
ax.axhline(50, color='gray', linestyle=':', alpha=0.7)
ax.set_xlabel('Número de importadores (ranking)')
ax.set_ylabel('% acumulado de autorizaciones')
ax.set_title('Concentración de la demanda por importador')
ax.legend()
plt.tight_layout()
guardar(plt.gcf(), '05_concentracion_importadores.png')
plt.show()
n80 = (cum <= 80).sum()
print(f'{n80} importadores acumulan el 80% de las autorizaciones (de {len(vc)} totales)')
"""),
    md("## 3. Tipo de solicitud por top 10 importadores"),
    code("""
top10 = df['IMPORTADOR'].value_counts().head(10).index
tab = pd.crosstab(df[df['IMPORTADOR'].isin(top10)]['IMPORTADOR'],
                  df[df['IMPORTADOR'].isin(top10)]['TIPO_SOLICITUD'])
fig, ax = plt.subplots(figsize=(11, 6))
sns.heatmap(tab, annot=True, fmt='d', cmap='Blues', ax=ax)
ax.set_title('Top 10 importadores × tipo de solicitud')
plt.tight_layout()
guardar(plt.gcf(), '05_heatmap_importador_tipo.png')
plt.show()
"""),
    md("## 4. Importador × principio activo (top 8 × top 8)"),
    code("""
ti = df['IMPORTADOR'].value_counts().head(8).index
tp = df['PRINCIPIO_ACTIVO'].value_counts().head(8).index
sub = df[df['IMPORTADOR'].isin(ti) & df['PRINCIPIO_ACTIVO'].isin(tp)]
tab2 = pd.crosstab(sub['IMPORTADOR'], sub['PRINCIPIO_ACTIVO'])
fig, ax = plt.subplots(figsize=(12, 7))
sns.heatmap(tab2, annot=True, fmt='d', cmap='Purples', ax=ax)
plt.xticks(rotation=45, ha='right', fontsize=8)
plt.yticks(fontsize=8)
ax.set_title('Especialización importador–medicamento (top 8×8)')
plt.tight_layout()
guardar(plt.gcf(), '05_heatmap_importador_medicamento.png')
plt.show()
"""),
    md("""## 📋 Hallazgos — Sprint 3 (Importadores)

| Hallazgo | Evidencia |
|----------|-----------|
| Oligopolio | Pocos importadores concentran la mayoría de autorizaciones |
| Especialización | Algunos importadores dominan medicamentos huérfanos específicos |
| Riesgo sistémico | Dependencia de pocos actores para enfermedades raras |
| Tipo solicitud | Grandes importadores atienden mix de paciente específico y colectivo |

**Siguiente:** `06_EDA_Temporal.ipynb`"""),
])

# ─── 06 TEMPORAL ─────────────────────────────────────────────────────────────
save("06_EDA_Temporal.ipynb", [
    md("""# 📅 Sprint 4 — EDA: Análisis temporal
**Insumo:** `mvnd_limpio.csv`

### Objetivos
- Tendencia anual 2018–2026 (2026 parcial)
- Estacionalidad mensual
- Evolución de urgencias y tipos de solicitud"""),
    md("## ⚙️ Configuración"),
    code(SETUP_CODE),
    code(IMPORTS_CODE),
    code(LOAD_CODE),
    md("## 1. Evolución anual"),
    code("""
anual = df.groupby('ANIO', as_index=False).size().rename(columns={'size': 'Autorizaciones'})
anual['Parcial'] = anual['ANIO'] == anual['ANIO'].max()

fig, ax = plt.subplots(figsize=(13, 6))
colores = ['#a9a9a9' if p else '#4472C4' for p in anual['Parcial']]
ax.bar(anual['ANIO'], anual['Autorizaciones'], color=colores, width=0.7)
for _, row in anual.iterrows():
    lbl = f"{row['Autorizaciones']:,}\\n(parcial)" if row['Parcial'] else f"{row['Autorizaciones']:,}"
    ax.text(row['ANIO'], row['Autorizaciones']+20, lbl, ha='center', fontsize=9, fontweight='bold')
comp = anual[~anual['Parcial']]
ax.plot(comp['ANIO'], comp['Autorizaciones'], 'ro--', linewidth=2, label='Tendencia (años completos)')
ax.set_title('Evolución anual de autorizaciones MVND')
ax.set_ylabel('Autorizaciones')
ax.legend()
plt.tight_layout()
guardar(plt.gcf(), '06_evolucion_anual.png')
plt.show()

anual['Var_%'] = anual['Autorizaciones'].pct_change() * 100
print(anual.to_string(index=False))
c18, c24 = anual.loc[anual['ANIO']==2018,'Autorizaciones'].iloc[0], anual.loc[anual['ANIO']==2024,'Autorizaciones'].iloc[0]
print(f'\\nCrecimiento 2018→2024: {(c24-c18)/c18*100:.1f}%')
"""),
    md("## 2. Estacionalidad mensual (2018–2025)"),
    code("""
df_comp = df[df['ANIO'] <= 2025]
mensual = df_comp.groupby('MES').size() / df_comp['ANIO'].nunique()
meses = {1:'Ene',2:'Feb',3:'Mar',4:'Abr',5:'May',6:'Jun',7:'Jul',8:'Ago',9:'Sep',10:'Oct',11:'Nov',12:'Dic'}

fig, ax = plt.subplots(figsize=(12, 5))
ax.bar([meses[m] for m in mensual.index], mensual.values, color='#4472C4')
ax.axhline(mensual.mean(), color='orange', linestyle='--', label=f'Promedio: {mensual.mean():.0f}')
ax.set_title('Promedio mensual de autorizaciones (2018–2025)')
ax.legend()
plt.tight_layout()
guardar(plt.gcf(), '06_estacionalidad_mensual.png')
plt.show()
"""),
    md("## 3. Trimestral"),
    code("""
trim = df[df['ANIO'] <= 2025].groupby(['ANIO','TRIMESTRE']).size().unstack(fill_value=0)
fig, ax = plt.subplots(figsize=(12, 5))
sns.heatmap(trim, annot=True, fmt='d', cmap='Blues', ax=ax)
ax.set_title('Autorizaciones por año y trimestre (2018–2025)')
plt.tight_layout()
guardar(plt.gcf(), '06_heatmap_trimestral.png')
plt.show()
"""),
    md("## 4. Tipo de solicitud por año"),
    code("""
pivot = pd.crosstab(df['ANIO'], df['TIPO_SOLICITUD'])
fig, ax = plt.subplots(figsize=(12, 4))
pivot.plot(kind='bar', stacked=True, ax=ax, color=['#4472C4','#ED7D31','#c00000'])
ax.set_title('Composición anual por tipo de solicitud')
ax.set_ylabel('Autorizaciones')
ax.legend(title='Tipo', bbox_to_anchor=(1.02, 1))
plt.xticks(rotation=0)
plt.tight_layout()
guardar(plt.gcf(), '06_tipo_solicitud_anual.png')
plt.show()
"""),
    md("## 5. Urgencias clínicas en el tiempo"),
    code("""
urg_anual = df.groupby('ANIO').agg(
    total=('ES_URGENCIA','count'),
    urgencias=('ES_URGENCIA','sum')
)
urg_anual['pct_urgencia'] = (urg_anual['urgencias'] / urg_anual['total'] * 100).round(2)

fig, ax1 = plt.subplots(figsize=(12, 5))
ax1.bar(urg_anual.index, urg_anual['urgencias'], color='#c00000', alpha=0.8, label='Urgencias')
ax1.set_ylabel('N° urgencias')
ax2 = ax1.twinx()
ax2.plot(urg_anual.index, urg_anual['pct_urgencia'], 'ko-', linewidth=2, label='% urgencias')
ax2.set_ylabel('% del total')
ax1.set_title('Urgencias clínicas por año')
fig.legend(loc='upper left')
plt.tight_layout()
guardar(plt.gcf(), '06_urgencias_anuales.png')
plt.show()
print(urg_anual)
"""),
    md("## 6. Top 3 medicamentos — tendencia anual"),
    code("""
top3 = df['PRINCIPIO_ACTIVO'].value_counts().head(3).index
trend = df[df['PRINCIPIO_ACTIVO'].isin(top3)].groupby(['ANIO','PRINCIPIO_ACTIVO']).size().unstack(fill_value=0)
fig, ax = plt.subplots(figsize=(12, 5))
for col in trend.columns:
    ax.plot(trend.index, trend[col], marker='o', linewidth=2, label=col[:40])
ax.set_title('Tendencia anual — Top 3 principios activos')
ax.set_ylabel('Autorizaciones')
ax.legend(fontsize=8)
plt.tight_layout()
guardar(plt.gcf(), '06_tendencia_top3_medicamentos.png')
plt.show()
"""),
    md("""## 📋 Hallazgos — Sprint 4 (Temporal)

| Hallazgo | Evidencia |
|----------|-----------|
| Tendencia creciente | Aumento sostenido 2018–2024 (~+61%) |
| 2026 parcial | Solo enero–abril; no comparar con años completos |
| Estacionalidad | Meses con mayor promedio identificables en 2018–2025 |
| Urgencias | Proporción relativamente estable (~9,5% global) con variación anual |

**Siguiente:** `07_Analisis_Estadistico.ipynb`"""),
])

# ─── 07 ESTADÍSTICO ──────────────────────────────────────────────────────────
save("07_Analisis_Estadistico.ipynb", [
    md("""# 📐 Sprint 4 — Análisis estadístico (diagnóstico)
**Insumo:** `mvnd_limpio.csv`

### Objetivos
- Probar asociación entre variables categóricas (chi-cuadrado)
- Medir fuerza con **V de Cramér**
- Responder: ¿urgencias y capítulos CIE-10 están asociados?"""),
    md("## ⚙️ Configuración"),
    code(SETUP_CODE),
    code(IMPORTS_CODE + "\n\nfrom scipy.stats import chi2_contingency"),
    code(LOAD_CODE),
    md("## Funciones estadísticas"),
    code("""
def cramers_v(tabla):
    chi2, _, _, _ = chi2_contingency(tabla)
    n = tabla.values.sum()
    r, k = tabla.shape
    return np.sqrt(chi2 / (n * min(r - 1, k - 1)))

def prueba_asociacion(df_sub, col_a, col_b, min_freq=5, titulo=''):
    tab = pd.crosstab(df_sub[col_a], df_sub[col_b])
    # Filtrar categorías muy pequeñas
    tab = tab.loc[tab.sum(axis=1) >= min_freq, tab.sum(axis=0) >= min_freq]
    chi2, p, dof, expected = chi2_contingency(tab)
    v = cramers_v(tab)
    print('=' * 60)
    print(titulo)
    print('=' * 60)
    print(f'Chi-cuadrado: {chi2:.2f}  |  gl: {dof}  |  p-valor: {p:.2e}')
    print(f"V de Cramér: {v:.3f}  → ", end='')
    if v < 0.1: print('asociación débil')
    elif v < 0.3: print('asociación moderada')
    else: print('asociación fuerte')
    print('Conclusión:', 'Asociación estadísticamente significativa (p<0.05)' if p < 0.05 else 'No significativa (p≥0.05)')
    return tab, chi2, p, v
"""),
    md("## 1. TIPO_SOLICITUD × CAPITULO_CIE10"),
    code("""
df_est = df[df['CAPITULO_CIE10'].notna()].copy()
# Top capítulos para tabla estable
top_cap = df_est['CAPITULO_CIE10'].value_counts().head(10).index
df_est = df_est[df_est['CAPITULO_CIE10'].isin(top_cap)]

tab1, chi2_1, p1, v1 = prueba_asociacion(
    df_est, 'TIPO_SOLICITUD', 'CAPITULO_CIE10',
    titulo='TIPO_SOLICITUD × CAPITULO_CIE10 (top 10 capítulos)'
)

fig, ax = plt.subplots(figsize=(11, 6))
sns.heatmap(tab1, annot=True, fmt='d', cmap='YlOrRd', ax=ax)
ax.set_title('Tabla de contingencia — Tipo solicitud × Capítulo CIE-10')
plt.tight_layout()
guardar(plt.gcf(), '07_chi2_tipo_capitulo.png')
plt.show()
"""),
    md("## 2. ES_URGENCIA × CAPITULO_CIE10"),
    code("""
df_est2 = df[df['CAPITULO_CIE10'].notna()].copy()
df_est2['URGENCIA'] = df_est2['ES_URGENCIA'].map({0: 'No urgencia', 1: 'Urgencia clínica'})
top_cap2 = df_est2['CAPITULO_CIE10'].value_counts().head(10).index
df_est2 = df_est2[df_est2['CAPITULO_CIE10'].isin(top_cap2)]

tab2, chi2_2, p2, v2 = prueba_asociacion(
    df_est2, 'URGENCIA', 'CAPITULO_CIE10',
    titulo='URGENCIA × CAPITULO_CIE10'
)

# % urgencia por capítulo
pct_urg = df_est2.groupby('CAPITULO_CIE10')['ES_URGENCIA'].mean().sort_values(ascending=False) * 100
fig, ax = plt.subplots(figsize=(11, 5))
pct_urg.plot(kind='barh', ax=ax, color='#c00000')
ax.set_xlabel('% urgencias dentro del capítulo')
ax.set_title('Proporción de urgencias clínicas por capítulo CIE-10')
plt.tight_layout()
guardar(plt.gcf(), '07_pct_urgencia_por_capitulo.png')
plt.show()
print(pct_urg.round(2))
"""),
    md("## 3. TIPO_SOLICITUD × FORMA_FARMACEUTICA (top categorías)"),
    code("""
top_f = df['FORMA_FARMACEUTICA'].value_counts().head(8).index
df_f = df[df['FORMA_FARMACEUTICA'].isin(top_f)]
tab3, chi2_3, p3, v3 = prueba_asociacion(
    df_f, 'TIPO_SOLICITUD', 'FORMA_FARMACEUTICA',
    titulo='TIPO_SOLICITUD × FORMA_FARMACEUTICA (top 8)'
)
fig, ax = plt.subplots(figsize=(10, 5))
sns.heatmap(tab3, annot=True, fmt='d', cmap='Greens', ax=ax)
plt.tight_layout()
guardar(plt.gcf(), '07_chi2_tipo_forma.png')
plt.show()
"""),
    md("## 4. Resumen de pruebas"),
    code("""
resumen = pd.DataFrame([
    {'Comparación': 'TIPO_SOLICITUD × CAPITULO_CIE10', 'Chi2': chi2_1, 'p_valor': p1, 'Cramers_V': v1},
    {'Comparación': 'URGENCIA × CAPITULO_CIE10', 'Chi2': chi2_2, 'p_valor': p2, 'Cramers_V': v2},
    {'Comparación': 'TIPO_SOLICITUD × FORMA_FARMACEUTICA', 'Chi2': chi2_3, 'p_valor': p3, 'Cramers_V': v3},
])
resumen['Significativo (p<0.05)'] = resumen['p_valor'] < 0.05
display(resumen.round(4))
resumen.to_excel('resumen_pruebas_estadisticas.xlsx', index=False)
print('✅ Exportado: resumen_pruebas_estadisticas.xlsx')
"""),
    md("""## 📋 Hallazgos — Análisis estadístico

| Prueba | Interpretación típica |
|--------|------------------------|
| TIPO × Capítulo | El tipo de solicitud **no se distribuye al azar** entre enfermedades (capítulos CIE-10) |
| Urgencia × Capítulo | Algunos capítulos presentan **mayor proporción** de urgencias clínicas |
| TIPO × Forma farmacéutica | Coherencia entre vía farmacéutica y mecanismo de solicitud |

> **Nota metodológica:** Con n > 10.000, el chi-cuadrado casi siempre es significativo; priorizar **V de Cramér** para interpretar la fuerza del efecto.

**Entregables finales:** Dashboard Power BI + informe ejecutivo.

---
*Proyecto MVND INVIMA — Unicomfacauca 2026*"""),
])

print("\n✅ 5 notebooks EDA generados.")
