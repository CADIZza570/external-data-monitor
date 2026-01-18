# 💰 CASH FLOW SYSTEM - La Chaparrita

Sistema de análisis de flujo de caja para Shopify integrado con webhooks en tiempo real.

## 🎯 Qué Hace Este Sistema

Este sistema convierte datos de ventas e inventario en **decisiones de dinero**:

- 💸 **Stockout Cost**: Cuánto dinero pierdes por productos agotados
- 📊 **DOI (Days of Inventory)**: Cuántos días te dura el inventario
- 🏆 **Clasificación ABC**: Qué productos generan más plata
- 💰 **Cash Flow Summary**: Vista completa de tu situación financiera

---

## 🚀 Quick Start

### 1️⃣ Ejecutar Migración (Una Sola Vez)

```bash
python3 migrate_db_cashflow.py
```

Esto crea las tablas y columnas necesarias en SQLite.

### 2️⃣ Sincronizar Datos Históricos (Una Sola Vez)

```bash
python3 sync_shopify_history.py
```

Esto jala órdenes de los últimos 60 días de Shopify y calcula el VDP (Venta Diaria Promedio).

⏱️ **Tiempo estimado**: 5-10 minutos para 600 órdenes

### 3️⃣ Importar Costos de Productos

Tienes 2 opciones:

**Opción A: Usar el CSV de ejemplo**

```bash
# Edita example_costs.csv con tus productos reales
# Luego usa curl o el test script
curl -X POST http://localhost:5000/api/costs/import \
  -F "file=@example_costs.csv"
```

**Opción B: Crear tu propio CSV**

Formato:
```csv
sku,cost_price,supplier,notes
BOOT-001,45.50,Proveedor A,Botas vaqueras talla 7
BOOT-002,52.00,Proveedor B,Botas texanas talla 8
```

### 4️⃣ Levantar el Servidor

```bash
python3 webhook_server.py
```

### 5️⃣ Probar los Endpoints

```bash
python3 test_cashflow.py
```

---

## 📡 API Endpoints

### 💸 Stockout Cost (Dinero Perdido)

```bash
GET /api/cashflow/stockout-cost
```

**Respuesta:**
```json
{
  "success": true,
  "total_lost_revenue": 1920.50,
  "stockouts_count": 12,
  "stockouts": [
    {
      "name": "Botas Vaqueras T8",
      "sku": "BOOT-008",
      "velocity_daily": 2.5,
      "days_out_of_stock": 14,
      "lost_revenue": 385.00
    }
  ]
}
```

**¿Qué Significa?**

- Si un producto se vende 2.5 unidades/día y lleva 14 días agotado
- Perdiste: `2.5 × 14 × (precio - costo)` = **$385**

---

### 📊 DOI (Días de Inventario)

```bash
GET /api/cashflow/doi
```

**Respuesta:**
```json
{
  "success": true,
  "products": [
    {
      "name": "Botas Rojas T9",
      "sku": "BOOT-009",
      "stock": 12,
      "velocity_daily": 1.8,
      "days_of_inventory": 6.7,
      "status": "CRÍTICO"
    }
  ]
}
```

**¿Qué Significa?**

- Con stock de 12 y ventas de 1.8/día
- Te quedan **6.7 días** antes de agotarte
- Status `CRÍTICO` = Necesitas reponer YA

---

### 🏆 Clasificación ABC

```bash
GET /api/cashflow/abc-classification
```

**Respuesta:**
```json
{
  "success": true,
  "total_revenue_30d": 15240.00,
  "category_stats": {
    "A": {"count": 8, "revenue": 12192.00},
    "B": {"count": 12, "revenue": 2286.00},
    "C": {"count": 20, "revenue": 762.00}
  },
  "products": [...]
}
```

**¿Qué Significa?**

- **Categoría A**: Top 20% de productos que generan 80% del dinero
- **Categoría B**: Siguiente 30% que genera 15%
- **Categoría C**: Último 50% que solo genera 5%

**Acción:** Repone SIEMPRE las "A" primero.

---

### 💰 Resumen Cash Flow

```bash
GET /api/cashflow/summary
```

**Respuesta:**
```json
{
  "summary": {
    "total_products": 85,
    "stockouts_count": 12,
    "lost_revenue": 1920.50,
    "inventory_value": 8450.00,
    "critical_stock_count": 7
  }
}
```

---

### 📥 Importar Costos

```bash
POST /api/costs/import
Content-Type: multipart/form-data

file=@costs.csv
```

**Respuesta:**
```json
{
  "success": true,
  "inserted": 45,
  "updated": 12,
  "total_processed": 57
}
```

---

### 📤 Exportar Costos

```bash
GET /api/costs/export
```

Descarga CSV con todos los costos.

---

## 🧮 Fórmulas Clave

### VDP (Venta Diaria Promedio)

```
VDP = Total vendido últimos 30 días / 30
```

**Ejemplo:**
- Vendiste 75 botas en 30 días
- VDP = 75 / 30 = **2.5 unidades/día**

---

### DOI (Días de Inventario)

```
DOI = Stock actual / VDP
```

**Ejemplo:**
- Stock: 18 botas
- VDP: 2.5 botas/día
- DOI = 18 / 2.5 = **7.2 días**

---

### Stockout Cost (Dinero Perdido)

```
Pérdida = VDP × Días agotado × (Precio - Costo)
```

**Ejemplo:**
- VDP: 2.5 unidades/día
- Días agotado: 10 días
- Precio: $85
- Costo: $45
- Margen: $40
- **Pérdida = 2.5 × 10 × 40 = $1,000**

---

## 🗂️ Estructura de Base de Datos

### Tabla: `products`

| Columna | Tipo | Descripción |
|---------|------|-------------|
| product_id | TEXT | ID del producto |
| name | TEXT | Nombre del producto |
| sku | TEXT | SKU |
| stock | INTEGER | Cantidad en inventario |
| price | REAL | Precio de venta |
| **cost_price** | REAL | **Costo de adquisición** |
| **velocity_daily** | REAL | **VDP (ventas/día)** |
| **total_sales_30d** | INTEGER | **Ventas últimos 30 días** |
| **last_sale_date** | TIMESTAMP | **Última venta** |
| **category** | TEXT | **Clasificación ABC** |

### Tabla: `orders_history`

| Columna | Tipo | Descripción |
|---------|------|-------------|
| order_id | TEXT | ID de la orden |
| product_id | TEXT | ID del producto |
| sku | TEXT | SKU |
| quantity | INTEGER | Cantidad vendida |
| price | REAL | Precio de venta |
| total_price | REAL | Total (precio × cantidad) |
| order_date | TIMESTAMP | Fecha de la orden |
| shop | TEXT | Tienda |

### Tabla: `product_costs`

| Columna | Tipo | Descripción |
|---------|------|-------------|
| sku | TEXT | SKU (único) |
| cost_price | REAL | Costo de adquisición |
| supplier | TEXT | Proveedor |
| notes | TEXT | Notas |
| last_updated | TIMESTAMP | Última actualización |

---

## 🎯 Flujo de Trabajo Recomendado

### **SETUP (Una sola vez)**

1. Ejecutar `migrate_db_cashflow.py`
2. Ejecutar `sync_shopify_history.py`
3. Importar costos vía `/api/costs/import`

### **OPERACIÓN DIARIA**

1. El webhook actualiza stock en tiempo real
2. Revisar `/api/cashflow/summary` cada mañana
3. Actuar sobre productos con DOI < 7 días
4. Reponer categoría A primero

### **SEMANAL**

1. Ejecutar `/api/cashflow/abc-classification` para re-clasificar
2. Revisar `/api/cashflow/stockout-cost` para cuantificar pérdidas
3. Exportar reporte a Google Sheets

---

## 🚨 Alertas Discord (Próximamente)

```python
# Configurar en webhook_server.py

if doi < 7 and category == 'A':
    send_discord_alert(
        f"🚨 STOCK CRÍTICO: {product.name}\n"
        f"Solo quedan {doi:.1f} días de inventario.\n"
        f"Categoría A - ¡Reponer YA!"
    )
```

---

## 📊 Dashboard Widgets (Próximamente)

Agregar al dashboard:

```html
<div class="widget">
  <h3>💸 Ventas Perdidas (Stockouts)</h3>
  <h1>$1,920</h1>
  <p>Esta semana</p>
  <button>Ver Detalles</button>
</div>

<div class="widget">
  <h3>📦 Stock Crítico</h3>
  <h1>7 productos</h1>
  <p>Menos de 7 días de inventario</p>
  <button>Generar Orden de Compra</button>
</div>
```

---

## 🐛 Troubleshooting

### Error: "No such table: orders_history"

**Solución:**
```bash
python3 migrate_db_cashflow.py
```

### Error: "SHOPIFY_STORE not configured"

**Solución:**
Agrega a `.env`:
```
SHOPIFY_STORE=tu-tienda.myshopify.com
SHOPIFY_ACCESS_TOKEN=shpat_xxxxxxxxxxxx
```

### Error: "No se pueden calcular métricas (VDP = 0)"

**Solución:**
```bash
# Necesitas sincronizar datos históricos primero
python3 sync_shopify_history.py
```

---

## 📈 Próximos Pasos

- [ ] Dashboard visual con widgets de Cash Flow
- [ ] Alertas Discord automáticas para stock crítico
- [ ] Botón "Generar Orden de Compra" que exporte CSV/PDF
- [ ] Forecast de ventas (predicción de demanda)
- [ ] Integración con proveedores (auto-pedido)

---

## 💡 Tips Pro

1. **Actualiza costos regularmente**: Los márgenes cambian
2. **Revisa ABC mensualmente**: Los productos cambian de categoría
3. **Prioriza la categoría A**: 80% de tu cash flow viene de ahí
4. **DOI < 7 días = Alerta**: Ya deberías haber pedido
5. **Stockout de categoría A = Emergencia**: Pierdes MUCHO dinero

---

## 🤝 Soporte

Si tienes dudas o errores:
1. Revisa los logs: `tail -f logs/webhook_server.log`
2. Ejecuta el test: `python3 test_cashflow.py`
3. Verifica la DB: `sqlite3 webhooks.db "SELECT * FROM products LIMIT 5;"`

---

**Hecho con ❤️ para La Chaparrita**

*Sistema diseñado para maximizar cash flow y minimizar stockouts.*
