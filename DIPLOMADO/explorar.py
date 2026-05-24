import pandas as pd

df = pd.read_excel("/sessions/laughing-stoic-cannon/mnt/DIPLOMADO/MEDICAMENTOS_VITALES_NO_DISPONIBLES_20260425.xlsx")

print("FORMA:", df.shape)
print("\nCOLUMNAS:")
for c in df.columns:
    print(" -", repr(c))
print("\nTIPOS:")
print(df.dtypes.to_string())
print("\nNULOS:")
nulos = df.isnull().sum()
pct = (nulos / len(df) * 100).round(2)
for col in df.columns:
    print(f"  {col}: {nulos[col]} ({pct[col]}%)")
print("\nDUPLICADOS:", df.duplicated().sum())
print("\nUNICOS POR COLUMNA:")
for col in df.columns:
    print(f"  {col}: {df[col].nunique()}")
print("\nPRIMERA FILA:")
row = df.iloc[0]
for k, v in row.items():
    print(f"  {k}: {v}")
