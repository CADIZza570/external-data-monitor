"""
Test manual básico para api_data_fetcher.py
No requiere pytest - solo Python estándar

Ejecutar:
    python3 test_manual.py
"""

import pandas as pd
import sys
import os
import tempfile
from datetime import datetime

# Importar funciones a testear
try:
    from api_data_fetcher import validate_data, process_data
    print("✅ Módulo api_data_fetcher importado correctamente\n")
except ImportError as e:
    print(f"❌ Error al importar: {e}")
    sys.exit(1)


def print_test_header(test_name):
    """Helper para imprimir cabeceras de tests"""
    print("=" * 60)
    print(f"🧪 {test_name}")
    print("=" * 60)


def test_validate_data_missing_columns():
    """TEST 1: DataFrame sin columnas requeridas debe fallar"""
    print_test_header("TEST 1: Validación con columnas faltantes")
    
    df_bad = pd.DataFrame({
        "id": [1, 2, 3],
        "name": ["Ana", "Luis", "María"]
    })
    
    try:
        validate_data(df_bad)
        print("❌ FALLO: Debería haber lanzado ValueError")
        return False
    except ValueError as e:
        print(f"✅ PASÓ: Error detectado correctamente")
        print(f"   Mensaje: {e}")
        return True


def test_validate_data_with_nulls():
    """TEST 2: DataFrame con valores nulos en columnas críticas"""
    print_test_header("TEST 2: Validación con valores nulos")
    
    df_nulls = pd.DataFrame({
        "id": [1, 2, 3],
        "name": ["Ana", "Luis", None],
        "username": ["ana123", "luis456", "maria789"],
        "email": ["ana@test.com", None, "maria@test.com"]
    })
    
    try:
        result = validate_data(df_nulls)
        print("✅ PASÓ: Función ejecutó sin crash")
        print("   Advertencias deberían estar en logs")
        return True
    except Exception as e:
        print(f"⚠️ ADVERTENCIA: Error inesperado: {e}")
        return False


def test_validate_data_valid():
    """TEST 3: DataFrame completamente válido"""
    print_test_header("TEST 3: Validación con datos correctos")
    
    df_valid = pd.DataFrame({
        "id": [1, 2, 3],
        "name": ["Ana García", "Luis Pérez", "María López"],
        "username": ["anagarcia", "luisperez", "marialopez"],
        "email": ["ana@example.com", "luis@example.com", "maria@example.com"]
    })
    
    try:
        result = validate_data(df_valid)
        print("✅ PASÓ: Validación exitosa")
        print(f"   Filas retornadas: {len(result)}")
        return True
    except Exception as e:
        print(f"❌ FALLO: No debería fallar con datos válidos: {e}")
        return False


def test_process_data_basic():
    """TEST 4: Procesamiento básico de datos"""
    print_test_header("TEST 4: Procesamiento de datos")
    
    # Crear CSV temporal
    temp_csv = tempfile.NamedTemporaryFile(
        mode='w',
        delete=False,
        suffix='.csv'
    )
    temp_csv.write("id,name,username,email,phone,website\n")
    temp_csv.write("1,Ana,ana123,ANA@TEST.COM,555-0001,ana.com\n")
    temp_csv.write("2,Luis,luis456,luis@test.com,555-0002,luis.com\n")
    temp_csv.write("2,Luis,luis456,luis@test.com,555-0002,luis.com\n")
    temp_csv.write("3,María,maria789,INVALID_EMAIL,555-0003,maria.com\n")
    temp_csv.close()
    
    try:
        result_path = process_data(temp_csv.name)
        
        if result_path and os.path.exists(result_path):
            df_clean = pd.read_csv(result_path)
            print("✅ PASÓ: Archivo procesado creado")
            print(f"   Registros originales: 4")
            print(f"   Registros limpios: {len(df_clean)}")
            print(f"   Duplicados eliminados: {4 - len(df_clean)}")
            
            if df_clean['email'].str.islower().all():
                print("   ✅ Emails normalizados a minúsculas")
            
            return True
        else:
            print("❌ FALLO: No se creó archivo de salida")
            return False
            
    except Exception as e:
        print(f"❌ FALLO: Error en procesamiento: {e}")
        return False
    finally:
        if os.path.exists(temp_csv.name):
            os.unlink(temp_csv.name)


def test_fetch_data_timeout():
    """TEST 5: Manejo de timeout (simulado)"""
    print_test_header("TEST 5: Manejo de errores de red")
    
    print("⚠️ Test manual requerido:")
    print("   1. Desconecta tu WiFi")
    print("   2. Ejecuta: python3 api_data_fetcher.py")
    print("   3. Verifica que:")
    print("      - El error se loguea correctamente")
    print("      - El script no crashea sin mensaje")
    print("      - Los reintentos se ejecutan")
    
    return None


def run_all_tests():
    """Ejecuta todos los tests y reporta resultados"""
    print("\n")
    print("🚀 INICIANDO SUITE DE TESTS")
    print(f"⏰ Tiempo: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n")
    
    tests = [
        test_validate_data_missing_columns,
        test_validate_data_with_nulls,
        test_validate_data_valid,
        test_process_data_basic,
        test_fetch_data_timeout
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append((test.__name__, result))
            print("\n")
        except Exception as e:
            print(f"💥 CRASH en {test.__name__}: {e}\n")
            results.append((test.__name__, False))
    
    print("=" * 60)
    print("📊 RESUMEN DE TESTS")
    print("=" * 60)
    
    passed = sum(1 for _, r in results if r is True)
    failed = sum(1 for _, r in results if r is False)
    manual = sum(1 for _, r in results if r is None)
    
    for name, result in results:
        if result is True:
            status = "✅ PASÓ"
        elif result is False:
            status = "❌ FALLÓ"
        else:
            status = "⚠️ MANUAL"
        print(f"{status} - {name}")
    
    print("\n")
    print(f"Total: {len(results)} tests")
    print(f"  ✅ Pasados: {passed}")
    print(f"  ❌ Fallidos: {failed}")
    print(f"  ⚠️ Manuales: {manual}")
    
    if failed == 0 and manual == 0:
        print("\n🎉 ¡Todos los tests pasaron!")
    elif failed == 0:
        print(f"\n✅ Tests automáticos OK. Ejecuta {manual} test(s) manual(es).")
    else:
        print(f"\n⚠️ Hay {failed} test(s) fallido(s). Revisa el código.")


if __name__ == "__main__":
    run_all_tests()