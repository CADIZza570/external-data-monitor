#!/usr/bin/env python3
# ============================================================
# 🧪 TEST SCRIPT - Probar Webhook Server
# ============================================================

import requests
import json

BASE_URL = "http://127.0.0.1:5001"

def test_health():
    """Prueba el endpoint de health check"""
    print("\n" + "="*50)
    print("🧪 TEST 1: Health Check")
    print("="*50)
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            print("✅ Health check PASSED")
            return True
        else:
            print("❌ Health check FAILED")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_webhook_shopify():
    """Prueba webhook Shopify simulado"""
    print("\n" + "="*50)
    print("🧪 TEST 2: Webhook Shopify (Simulación)")
    print("="*50)
    
    payload = {
        "products": [
            {
                "title": "Camiseta Roja",
                "variants": [
                    {"id": 101, "title": "S", "inventory_quantity": 3, "last_sold_date": "2025-12-10"},
                    {"id": 102, "title": "M", "inventory_quantity": 0, "last_sold_date": "2025-01-15"}
                ]
            },
            {
                "title": "Pantalón Azul",
                "variants": [
                    {"id": 201, "title": "32", "inventory_quantity": 15, "last_sold_date": "2025-12-20"}
                ]
            }
        ]
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/webhook/shopify",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            print("✅ Webhook Shopify PASSED")
            return True
        else:
            print("❌ Webhook Shopify FAILED")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_low_stock():
    """Prueba detección de stock bajo"""
    print("\n" + "="*50)
    print("🧪 TEST 3: Detección Stock Bajo")
    print("="*50)
    
    payload = {
        "products": [
            {"title": "Producto Crítico", "variants": [{"id": 301, "title": "Único", "inventory_quantity": 1}]},
            {"title": "Producto Agotado", "variants": [{"id": 302, "title": "Único", "inventory_quantity": 0}]},
            {"title": "Producto OK", "variants": [{"id": 303, "title": "Único", "inventory_quantity": 100}]}
        ]
    }
    
    try:
        response = requests.post(f"{BASE_URL}/webhook/shopify", json=payload)
        data = response.json()
        low_stock_count = data['alerts']['low_stock_count']
        
        print(f"Productos con stock bajo: {low_stock_count}")
        
        if low_stock_count == 2:
            print("✅ Detección stock bajo PASSED")
            return True
        else:
            print(f"⚠️ Esperábamos 2, obtuvimos {low_stock_count}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 INICIANDO TESTS")
    print("="*60)
    
    results = [
        ("Health Check", test_health()),
        ("Webhook Shopify", test_webhook_shopify()),
        ("Stock Bajo", test_low_stock())
    ]
    
    print("\n" + "="*60)
    print("📊 RESUMEN")
    print("="*60)
    
    passed = sum(1 for _, r in results if r)
    for name, result in results:
        print(f"   {name}: {'✅ PASSED' if result else '❌ FAILED'}")
    
    print(f"\n   Total: {passed}/{len(results)} tests pasados")
    
    if passed == len(results):
        print("\n🎉 ¡TODOS LOS TESTS PASARON!")
