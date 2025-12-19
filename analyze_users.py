import pandas as pd

def analyze_data(csv_path: str):
    """Analiza datos usando groupby() - Mes 2 requisito.
    
    Ejemplos de análisis:
    1. Contar usuarios por dominio de email
    2. Identificar dominios más comunes
    3. Detectar patrones en datos
    """
    print("\n" + "="*60)
    print("📊 ANÁLISIS DE DATOS CON GROUPBY (Mes 2)")
    print("="*60)
    
    df = pd.read_csv(csv_path)
    
    # Extraer dominio del email
    df['email_domain'] = df['email'].str.split('@').str[1]
    
    # ANÁLISIS 1: Contar usuarios por dominio
    print("\n1️⃣ Usuarios por dominio de email:")
    domain_counts = df.groupby('email_domain').size()
    print(domain_counts)
    
    # ANÁLISIS 2: Dominio más popular
    most_common = domain_counts.idxmax()
    print(f"\n🏆 Dominio más común: {most_common} ({domain_counts.max()} usuarios)")
    
    # ANÁLISIS 3: Agrupar por ciudad (si existe)
    if 'city' in df.columns:
        print("\n2️⃣ Usuarios por ciudad:")
        city_counts = df.groupby('city').size().sort_values(ascending=False)
        print(city_counts.head(5))
    
    # ANÁLISIS 4: Estadísticas por grupo
    print("\n3️⃣ Estadísticas detalladas por dominio:")
    stats = df.groupby('email_domain').agg({
        'id': 'count',      # Contar registros
        'name': 'first',    # Primer nombre de ese grupo
        'email': 'count'    # Total de emails
    }).rename(columns={'id': 'total_usuarios'})
    print(stats)
    
    return df


# EJEMPLO DE USO
if __name__ == "__main__":
    # Usar el CSV más reciente de output/
    import os
    import glob
    
    csv_files = glob.glob("output/*_clean.csv")
    if csv_files:
        latest_csv = max(csv_files, key=os.path.getctime)
        print(f"📂 Analizando: {latest_csv}")
        
        result = analyze_data(latest_csv)
        
        print("\n✅ Análisis completado")
        print("="*60)
    else:
        print("❌ No se encontraron archivos CSV en output/")