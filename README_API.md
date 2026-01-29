# La Chaparrita - Cash Flow API

API para gestión de inventario, análisis financiero y optimización de compras.

---

## 🔐 Authentication

⚠️ **Estado Actual:** Sistema sin autenticación
🔜 **Próximamente:** API Keys con header `X-API-Key`

**Recomendación:** Usar solo en red interna o detrás de firewall/VPN hasta implementar auth.

---

## 📊 Endpoints Disponibles

### 1. Health Check
Verifica que el servidor esté operativo.

```bash
curl https://tranquil-freedom-production.up.railway.app/health
```

**Respuesta:**
```json
{
  "status": "healthy",
  "service": "webhook-shopify-automation",
  "version": "2.5",
  "timestamp": "2026-01-28T15:30:00"
}
```

---

### 2. Resumen de Cash Flow
Obtiene métricas financieras clave del inventario.

```bash
curl "https://tranquil-freedom-production.up.railway.app/api/cashflow/summary?shop=la-chaparrita"
```

**Parámetros:**
- `shop` (string, opcional): Nombre de la tienda

**Respuesta:**
```json
{
  "success": true,
  "summary": {
    "total_products": 150,
    "inventory_value": 45000.50,
    "stockouts_count": 3,
    "lost_revenue": 1250.00,
    "critical_stock_count": 12
  }
}
```

**🚨 Alertas Centinela:**
- Inventory < $10,000 → Warning de stock bajo
- Stockouts > 5 → Alerta crítica
- Critical stock > 10 → Atención requerida

---

### 3. Calculadora de Reorden (Optimización de Presupuesto)
Calcula lista optimizada de compras según presupuesto y lead time.

```bash
curl "https://tranquil-freedom-production.up.railway.app/api/reorder-calculator?budget=5000&lead_time=14&shop=la-chaparrita"
```

**Parámetros:**
- `budget` (float, default: 5000): Presupuesto disponible (0 - 1,000,000)
- `lead_time` (int, default: 14): Días de reposición (1 - 90)
- `shop` (string, opcional): Filtro por tienda

**Respuesta:**
```json
{
  "budget": 5000.0,
  "used": 4850.25,
  "remaining": 149.75,
  "utilization_pct": 97.0,
  "shopping_list": [
    {
      "sku": "SOMB-ARCO-09",
      "name": "Sombrero Arcoiris - Talla 9",
      "shop": "la-chaparrita",
      "units_needed": 25,
      "unit_cost": 45.50,
      "total_cost": 1137.50,
      "priority": "A",
      "urgency": "3 días",
      "current_stock": 5
    }
  ],
  "items_count": 12,
  "categories_breakdown": {
    "A": 3500.00,
    "B": 1200.25,
    "C": 150.00
  },
  "lead_time_days": 14
}
```

**🔥 Detección de Demanda Explosiva:**
- Velocity > 50% promedio últimos 3 días → Warning de spike estacional

---

### 4. Clasificación ABC
Analiza productos según Pareto (80/20) por revenue.

```bash
curl "https://tranquil-freedom-production.up.railway.app/api/cashflow/abc-classification?shop=la-chaparrita"
```

**Parámetros:**
- `shop` (string, opcional): Filtro por tienda

**Respuesta:**
```json
{
  "success": true,
  "products": [
    {
      "sku": "SOMB-ARCO-09",
      "name": "Sombrero Arcoiris - Talla 9",
      "revenue_30d": 15000.50,
      "cumulative_pct": 25.5,
      "category": "A",
      "priority": "ALTA"
    }
  ],
  "summary": {
    "category_A_count": 15,
    "category_B_count": 30,
    "category_C_count": 105,
    "category_A_revenue_pct": 80.2
  }
}
```

---

### 5. Días de Inventario (DOI)
Calcula cuántos días durará el stock actual.

```bash
curl "https://tranquil-freedom-production.up.railway.app/api/cashflow/doi?shop=la-chaparrita"
```

**Respuesta:**
```json
{
  "success": true,
  "average_doi": 22.5,
  "products": [
    {
      "sku": "SOMB-ARCO-09",
      "name": "Sombrero Arcoiris - Talla 9",
      "stock": 45,
      "velocity_daily": 3.2,
      "days_of_inventory": 14,
      "status": "OK"
    }
  ]
}
```

---

### 6. Trending de Ventas
Top productos más vendidos en período específico.

```bash
curl "https://tranquil-freedom-production.up.railway.app/api/analytics/trending-sizes?days=30&limit=10"
```

**Parámetros:**
- `days` (int, default: 30): Período a analizar (1 - 365)
- `limit` (int, default: 10): Top N productos (1 - 100)

---

### 7. Importar Costos (CSV)
Importa costos de productos desde CSV.

```bash
curl -X POST \
  -F "file=@costos.csv" \
  https://tranquil-freedom-production.up.railway.app/api/costs/import
```

**Formato CSV:**
```csv
sku,cost_price,supplier,notes
SOMB-001,45.50,Proveedor A,Sombrero vaquero
SOMB-002,52.00,Proveedor B,Sombrero texano
```

---

## 🚦 Rate Limits

- **General:** 100 requests/hora por IP
- **Webhooks Shopify:** 100 requests/hora
- **CSV Upload:** 50 requests/hora

---

## ⚠️ Límites de Seguridad

- Max payload: 16MB
- Max products per request: 10,000
- Parámetros con validación automática (min/max)

---

## 🔧 Próximas Features (Roadmap)

- [ ] Autenticación con API Keys
- [ ] Swagger/OpenAPI documentation
- [ ] WebSocket para alertas real-time
- [ ] Dashboard UI con Chart.js
- [ ] Retry logic en integraciones
- [ ] Tests automatizados

---

## 📞 Soporte

- **Issues:** https://github.com/CADIZza570/external-data-monitor/issues
- **Version:** 2.5
- **Última actualización:** 2026-01-28

---

## 🎯 Ejemplo Completo con Auth (próximamente)

```bash
# Una vez implementado API keys:
curl -H "X-API-Key: sk_live_abc123..." \
  "https://tranquil-freedom-production.up.railway.app/api/cashflow/summary?shop=la-chaparrita"
```

---

**Desarrollado con ❤️ por Claude Code**
Sistema brillante para La Chaparrita 🌵
