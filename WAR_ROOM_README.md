# 🦈 WAR ROOM - TIBURÓN PREDICTIVO

## Centro de Mando Táctico para Dominar el Mercado de Columbus, OH

---

## 🎯 **VISIÓN**

El **War Room** no es un dashboard - es un **palacio de cristal y acero** donde La Chaparrita controla el mercado de Ohio con un clic. Transformación radical del dashboard tradicional en un **centro de mando táctico** que respira la energía depredadora del Tiburón.

---

## 🔥 **CARACTERÍSTICAS PRINCIPALES**

### 1. **Estética Cyber-Retail**
- **Dark Theme Gélido**: Refleja -21°C de Columbus con gradientes ice-black → deep-black
- **Neón Estratégico**: Verde (#10b981) para estrellas, Rojo sangre (#ef4444) para dead stock
- **Animaciones Sutiles**: Pulse indicators, hover effects, rotating gradients
- **Tipografía Táctica**: Inter font, weight 700-800 para headers

### 2. **⚡ PULSO PREDICTIVO - Corazón del War Room**
```
╔═══════════════════════════════════════════════════════════╗
║  🦈 PULSO PREDICTIVO - 31 Enero 2026
╚═══════════════════════════════════════════════════════════╝

💰 CASH FLOW SNAPSHOT:
├─ Inventario Total: $9,180.00
├─ Productos Totales: 11
├─ Stock Crítico: 3
└─ Stockouts: 0

🌡️ CONTEXTO CLIMÁTICO:
├─ Columbus, OH: -9.6°C
└─ Próximo Feriado: Valentine's Day (14 días)

🎯 PRÓXIMA ACCIÓN:
└─ Monitorear oportunidades Instinto Depredador ↓
```

**El Sticker Predictivo domina el centro del panel**, dictando la narrativa de guerra del día. Auto-refresh cada 60s.

### 3. **🔥 MAPA DE CALOR - Inventario Dinámico**

Sustituye tablas aburridas por **heatmap visual** con 3 estados:

| Color | Condición | Criterio |
|-------|-----------|----------|
| **Verde Neón** 🟢 | Estrella | Velocity ≥ 2.0/día |
| **Naranja** 🟠 | Warning | 0.5 ≤ Velocity < 2.0 |
| **Rojo Sangre** 🔴 | Dead Stock | Velocity < 0.5/día |

**Click en celda roja** → Sugiere Parasite Bundle inmediato

**Layout:**
```
┌─────┬─────┬─────┬─────┐
│ SKU │ SKU │ SKU │ SKU │
│ 150 │  45 │   3 │  87 │
│ 4.5 │ 2.1 │ 0.0 │ 1.8 │
└─────┴─────┴─────┴─────┘
```

### 4. **📊 GRÁFICOS DE ASALTO**

#### **Clima vs ROI (Chart.js Line Chart)**
Visualización dual-axis que cruza:
- **Eje Y Izquierdo (Azul)**: Temperatura Columbus (°C)
- **Eje Y Derecho (Verde)**: ROI Proyectado (%)

**Insight:** Cuando temperatura baja, ROI sube (productos winter)

#### **Velocity Trends (Chart.js Bar Chart)**
Top 10 productos por velocity, coloreados:
- Verde: Velocity ≥ 2.0
- Naranja: 1.0 ≤ Velocity < 2.0
- Rojo: Velocity < 1.0

### 5. **🎯 INSTINTO DEPREDADOR - One-Click Actions**

Sección dedicada a **oportunidades de captura** con botones ejecutables:

#### **💹 PRICE SURGE**
```
┌──────────────────────────────────────┐
│ 💹 PRICE SURGE                       │
│ Guantes Arctic Waterproof           │
│ SKU: GLOVES-ARC-01                   │
│ Precio Actual: $45.99                │
│ Precio Surge: $52.89                 │
│ Duración: 48h                        │
│                                      │
│ +18.2% ROI                           │
│                                      │
│ [🚀 EJECUTAR SURGE]                  │
└──────────────────────────────────────┘
```

**Click botón** → Ejecuta `POST /api/execute-price-surge` con confirmación

#### **📦 PARASITE BUNDLE**
```
┌──────────────────────────────────────┐
│ 📦 PARASITE BUNDLE                   │
│ Botas Waterproof + Sandalias Verano │
│ Estrella: BOOTS-WP-01 (2.8/día)     │
│ Dead Stock: SANDALS-BEACH-01 (150)  │
│ Bundle Price: $89.99                 │
│ Descuento: 60%                       │
│                                      │
│ +127.5% ROI                          │
│                                      │
│ [🎯 EJECUTAR BUNDLE]                 │
└──────────────────────────────────────┘
```

**Click botón** → Ejecuta `POST /api/execute-bundle` con confirmación

**Si no hay oportunidades:**
```
⏳ Sin oportunidades activas
El Tiburón espera condiciones óptimas...
```

### 6. **📈 EVOLUCIÓN PREDICTIVA (7 días)**

Panel de métricas que muestra **Opportunity Cost** y aprendizaje por clics:

```
┌─────────────────────┬─────────────────────┐
│ $1,250              │ 45                  │
│ Opportunity Cost 7d │ Interacciones       │
│ -2.3% vs anterior   │ +18.5% vs anterior  │
├─────────────────────┼─────────────────────┤
│ 12                  │ 26.7%               │
│ Ejecuciones         │ Tasa Conversión     │
│ +12 esta semana     │ +4.2pp vs anterior  │
└─────────────────────┴─────────────────────┘
```

**Métricas Clave:**
- **Opportunity Cost 7d**: Dinero perdido por NO ejecutar sugerencias
- **Interacciones**: Clics totales en botones [Surge] [Bundle] [Reorden]
- **Ejecuciones**: Acciones confirmadas y ejecutadas
- **Tasa Conversión**: % de clics que se convierten en ejecuciones
- **Cambios vs semana anterior**: Verde (+) o Rojo (-)

**Objetivo:** Mostrar cómo el aprendizaje por clics afila el Monte Carlo

---

## 🏗️ **ARQUITECTURA**

### **Stack Tecnológico**
```
Frontend:
├─ HTML5 + CSS3 (Custom Cyber-Retail Theme)
├─ Vanilla JavaScript (ES6+)
├─ Chart.js 4.4.1 (Gráficos)
└─ Fetch API (REST calls)

Backend:
├─ Flask route: /war-room
├─ API endpoints existentes:
│  ├─ /api/cashflow/summary
│  ├─ /api/cashflow/abc-classification
│  ├─ /api/predator-suggestions
│  ├─ /api/execute-price-surge
│  └─ /api/execute-bundle
└─ Auto-refresh: 60s interval
```

### **Flujo de Datos**
```
┌─────────────────┐
│   War Room UI   │
└────────┬────────┘
         │
         ├─ loadSticker() ──────────► /api/cashflow/summary
         ├─ loadProducts() ─────────► /api/cashflow/abc-classification
         ├─ loadOpportunities() ────► /api/predator-suggestions
         └─ loadEvolution() ────────► /api/evolution/7d (TODO)
                │
                ▼
         ┌─────────────┐
         │  Render UI  │
         │  - Heatmap  │
         │  - Charts   │
         │  - Buttons  │
         └─────────────┘
                │
                ▼ (User clicks button)
         ┌─────────────┐
         │   Execute   │
         │  POST /api  │
         └─────────────┘
```

### **Endpoints Consumidos**

| Endpoint | Método | Uso en War Room |
|----------|--------|-----------------|
| `/api/cashflow/summary` | GET | Header stats + Sticker |
| `/api/cashflow/abc-classification` | GET | Heatmap + Velocity chart |
| `/api/predator-suggestions` | GET | Oportunidades Instinto Depredador |
| `/api/execute-price-surge` | POST | Botón "Ejecutar Surge" |
| `/api/execute-bundle` | POST | Botón "Ejecutar Bundle" |
| `/api/evolution/7d` | GET | Evolución Predictiva (TODO) |

---

## 🚀 **DEPLOYMENT**

### **Acceso**
```
Producción: https://tranquil-freedom-production.up.railway.app/war-room
Local: http://localhost:5000/war-room
```

### **Deployment Railway**
```bash
# 1. Agregar archivos
git add templates/war_room.html webhook_server.py WAR_ROOM_README.md

# 2. Commit
git commit -m "Feat: War Room - Centro de Mando Táctico Tiburón 🦈

- Estética Cyber-Retail (dark theme gélido -21°C vibes)
- Mapa de Calor dinámico (verde neón estrellas, rojo sangre dead stock)
- Gráficos de Asalto Chart.js (Clima vs ROI)
- Instinto Depredador one-click (Price Surge + Bundles)
- Evolución Predictiva (Opportunity Cost 7d)
- Sticker Predictivo como corazón del panel
- Auto-refresh 60s, responsive mobile

War Room ready para dominar Ohio con un clic 🔥"

# 3. Push
git push origin main

# 4. Verificar deployment
curl -I https://tranquil-freedom-production.up.railway.app/war-room
```

### **Testing Local**
```bash
# 1. Iniciar Flask
python webhook_server.py

# 2. Abrir War Room
open http://localhost:5000/war-room

# 3. Verificar consola browser
# Debería mostrar:
# 🦈 Inicializando War Room...
# ✅ War Room inicializado
```

---

## 🎨 **GUÍA DE ESTILO**

### **Paleta de Colores**
```css
--ice-black: #0a0e15      /* Background principal */
--deep-black: #111827     /* Background secundario */
--steel-gray: #1f2937     /* Secciones, cards */
--frost-gray: #374151     /* Borders, disabled */

--neon-green: #10b981     /* Estrellas, ROI positivo */
--blood-red: #ef4444      /* Dead stock, alerts */
--ice-blue: #3b82f6       /* Charts, links */
--arctic-cyan: #06b6d4    /* Títulos, accents */
--gold-predator: #f59e0b  /* Oportunidades, CTA */
--white-frost: #f9fafb    /* Texto principal */
```

### **Tipografía**
```css
Familia: 'Inter', -apple-system, BlinkMacSystemFont, system-ui
Pesos: 400 (normal), 600 (semibold), 700 (bold), 800 (extrabold)

Títulos: 2rem / 800 weight / gradient cyan → green
Subtítulos: 1.25rem / 700 weight / white-frost
Body: 0.875rem / 400 weight / frost-gray
Métricas: 1.5-2rem / 800 weight / arctic-cyan
```

### **Animaciones**
```css
Pulse indicator: 2s infinite (opacity + scale)
Rotate gradient: 20s linear infinite
Hover cards: 0.3s ease (transform translateY -2px)
Button active: transform translateY(0)
Spinner: 1s linear infinite rotate
```

---

## 📊 **PRÓXIMOS NIVELES**

### **Fase 1: Completar Endpoints** ✅ CURRENT
- [x] Sticker Predictivo
- [x] Heatmap Inventario
- [x] Gráficos Clima vs ROI
- [x] Instinto Depredador buttons
- [ ] **TODO: `/api/evolution/7d`** (Opportunity Cost real)

### **Fase 2: Interactividad Avanzada**
- [ ] Click celda heatmap → Modal detalles producto
- [ ] Gráfico interactivo (hover tooltip datos exactos)
- [ ] Filtros: timeframe 7d/30d/90d
- [ ] Toggle modo "Ejecutivo" (métricas grandes) vs "Técnico" (tablas)

### **Fase 3: Tiempo Real**
- [ ] WebSocket para updates live (sin refresh)
- [ ] Notificaciones browser cuando nueva oportunidad
- [ ] Animación cuando oportunidad ejecutada (confetti)

### **Fase 4: Mobile Optimization**
- [ ] PWA (Progressive Web App)
- [ ] Touch gestures (swipe heatmap cells)
- [ ] Mobile-first layout (grid 1 columna)

### **Fase 5: AI Insights**
- [ ] Panel "Predicciones IA" (próximas 72h)
- [ ] Alertas predictivas: "En 3 días stockout BOOTS-WP-01"
- [ ] Comparación predicción vs real (accuracy tracking)

---

## 🔧 **TROUBLESHOOTING**

### **War Room no carga (404)**
```bash
# Verificar archivo existe
ls -la templates/war_room.html

# Verificar ruta Flask
grep -n "war-room" webhook_server.py
```

### **API calls fallan (Network Error)**
```bash
# Verificar servidor Flask corriendo
curl http://localhost:5000/health

# Verificar endpoints API
curl http://localhost:5000/api/cashflow/summary
curl http://localhost:5000/api/predator-suggestions
```

### **Gráficos no renderizan**
```javascript
// Abrir consola browser (F12)
// Verificar errores Chart.js
// Verificar CDN Chart.js cargó:
console.log(Chart);
// Debería mostrar: function Chart() {...}
```

### **Datos no se actualizan**
```javascript
// Auto-refresh está activo?
// Verificar en consola browser cada 60s:
// 🔄 Refreshing War Room...

// Forzar refresh manual:
location.reload();
```

---

## 📚 **REFERENCIAS**

### **APIs Documentadas**
- [Cash Flow API](cashflow_api.py) - Endpoints `/api/cashflow/*`
- [Market Predator](market_predator.py) - Lógica Price Surge + Bundles
- [Pulse Scheduler](pulse_scheduler.py) - Sticker Predictivo generator

### **Dependencias**
- [Chart.js Docs](https://www.chartjs.org/docs/latest/)
- [Flask Routing](https://flask.palletsprojects.com/routing/)
- [CSS Grid Layout](https://css-tricks.com/snippets/css/complete-guide-grid/)

---

## 🦈 **FILOSOFÍA WAR ROOM**

> **"No quiero un visor de datos, quiero un centro de mando táctico que respire la energía de La Chaparrita."**

El War Room NO es:
- ❌ Un dashboard de métricas
- ❌ Un panel de admin tradicional
- ❌ Tablas con scroll infinito

El War Room ES:
- ✅ Un **arma táctica** para dominar mercado
- ✅ Un **cerebro visual** que piensa por ti
- ✅ Un **puño de acero** que ejecuta con un clic

**Cada pixel comunica urgencia, cada métrica grita oportunidad, cada botón es un gatillo listo para disparar.**

---

## 🎯 **MANTRA**

```
El Tiburón no espera.
El Tiburón no duda.
El Tiburón EJECUTA.
```

---

**🦈 War Room Ready - Domina Ohio con un clic**

*Desarrollado con visión radical de Gemini y cirugía de Claude*
