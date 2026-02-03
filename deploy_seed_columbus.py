#!/usr/bin/env python3
"""
🚀 Deploy Seed Columbus - Helper Script

Ejecuta seed remoto en Railway via API endpoint.
Usa esto en lugar de copiar DB o SSH.
"""

import requests
import json
import sys
import os

API_URL = "https://tranquil-freedom-production.up.railway.app"
ADMIN_KEY = os.getenv("ADMIN_SEED_KEY", "tiburon-seed-2026")


def test_endpoint_exists():
    """Verificar que endpoint esté disponible"""
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Servicio Railway está UP")
            return True
        else:
            print(f"⚠️ Servicio responde pero no healthy: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Servicio Railway no disponible: {e}")
        return False


def seed_dry_run():
    """Ejecutar dry run para preview"""
    print("\n🧪 Ejecutando DRY RUN...")

    try:
        response = requests.post(
            f"{API_URL}/api/admin/seed-columbus",
            json={"admin_key": ADMIN_KEY, "dry_run": True},
            timeout=15
        )

        if response.status_code == 200:
            data = response.json()
            print("✅ Dry run exitoso!\n")
            print(json.dumps(data, indent=2))
            return True
        elif response.status_code == 404:
            print("❌ Endpoint no encontrado (404)")
            print("   Railway puede estar deployando todavía...")
            print("   Espera 1-2 minutos y reintenta")
            return False
        elif response.status_code == 401:
            print("❌ No autorizado - verifica ADMIN_SEED_KEY")
            return False
        else:
            print(f"❌ Error {response.status_code}: {response.text[:200]}")
            return False

    except Exception as e:
        print(f"❌ Error ejecutando dry run: {e}")
        return False


def seed_production():
    """Ejecutar seed REAL en producción"""
    print("\n🦈 Ejecutando SEED REAL en Railway...")
    print("⚠️  Esto va a insertar datos en la DB de producción!\n")

    confirm = input("Confirmar? (escribe 'SI' en mayúsculas): ")

    if confirm != "SI":
        print("❌ Cancelado por usuario")
        return False

    try:
        response = requests.post(
            f"{API_URL}/api/admin/seed-columbus",
            json={"admin_key": ADMIN_KEY, "dry_run": False},
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            print("\n✅ SEED COMPLETADO EXITOSAMENTE!\n")
            print(json.dumps(data, indent=2))

            print("\n" + "="*60)
            print("🎯 PRÓXIMOS PASOS:")
            print("="*60)
            print("1. Verificar datos:")
            print(f"   curl {API_URL}/api/cashflow/summary | python3 -m json.tool")
            print("\n2. Test Pulso manual:")
            print(f"   Ver Discord en próximo pulso diario (8:00 AM)")
            print("\n3. Verificar productos:")
            print(f"   curl {API_URL}/api/products | python3 -m json.tool")
            print("="*60)

            return True
        else:
            print(f"❌ Error {response.status_code}: {response.text[:500]}")
            return False

    except Exception as e:
        print(f"❌ Error ejecutando seed: {e}")
        return False


def main():
    print("="*60)
    print("🦈 TIBURÓN PREDICTIVO - Deploy Seed Columbus")
    print("="*60)

    # 1. Test servicio
    if not test_endpoint_exists():
        sys.exit(1)

    # 2. Dry run
    print("\nOpción 1: Dry run (preview sin insertar)")
    print("Opción 2: Seed REAL (insertar en producción)")
    print("Opción 3: Salir")

    choice = input("\nElegí opción (1/2/3): ").strip()

    if choice == "1":
        seed_dry_run()
    elif choice == "2":
        if seed_dry_run():
            print("\n" + "-"*60)
            seed_production()
        else:
            print("❌ Dry run falló - no se puede ejecutar seed real")
    elif choice == "3":
        print("👋 Saliendo...")
    else:
        print("❌ Opción inválida")


if __name__ == "__main__":
    main()
