#!/usr/bin/env python3
"""
💬 INTERACTIVE HANDLER - Botones Discord/WhatsApp para acciones
Convierte notificaciones en interfaces interactivas
"""

import os
import json
import requests
from typing import Dict, List, Optional
from datetime import datetime

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")


class InteractiveHandler:
    """Manejador de interfaces interactivas (botones, select menus)"""

    def __init__(self, discord_webhook_url: str = DISCORD_WEBHOOK_URL):
        self.discord_webhook = discord_webhook_url

    def send_interactive_message(
        self,
        content: str,
        actions: List[Dict],
        embed: Optional[Dict] = None
    ) -> bool:
        """
        Envía mensaje con botones interactivos a Discord

        Args:
            content: Texto principal del mensaje
            actions: Lista de acciones/botones
                [
                    {
                        "label": "Aprobar Reorden",
                        "style": "success",  # success|danger|primary|secondary
                        "action_id": "approve_reorder_SOMB-ARCO-09_25",
                        "url": "https://tu-servidor.com/api/execute-reorder"
                    }
                ]
            embed: Opcional - Discord embed para formato rico

        Returns:
            bool - True si envío exitoso
        """
        if not self.discord_webhook:
            print("⚠️ Discord webhook no configurado")
            return False

        # Discord usa "components" para botones
        components = []

        if actions:
            # Agrupar botones en rows (máx 5 por row)
            action_row = {
                "type": 1,  # Action Row
                "components": []
            }

            for action in actions[:5]:  # Máx 5 botones
                button = {
                    "type": 2,  # Button
                    "label": action["label"],
                    "style": self._get_button_style(action.get("style", "primary")),
                    "custom_id": action.get("action_id", f"action_{len(components)}")
                }

                # Si tiene URL, es un Link Button (no requiere custom_id)
                if action.get("url"):
                    button["style"] = 5  # Link style
                    button["url"] = action["url"]
                    if "custom_id" in button:
                        del button["custom_id"]

                action_row["components"].append(button)

            components.append(action_row)

        payload = {
            "content": content,
            "components": components
        }

        if embed:
            payload["embeds"] = [embed]

        try:
            response = requests.post(
                self.discord_webhook,
                json=payload,
                timeout=10
            )

            if response.status_code in [200, 204]:
                print(f"✅ Mensaje interactivo enviado a Discord")
                return True
            else:
                print(f"⚠️ Discord webhook failed: {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ Error enviando a Discord: {e}")
            return False

    def _get_button_style(self, style: str) -> int:
        """
        Convierte nombre de estilo a código Discord

        Estilos Discord:
        1 = Primary (blurple)
        2 = Secondary (grey)
        3 = Success (green)
        4 = Danger (red)
        5 = Link (grey, requiere URL)
        """
        styles = {
            "primary": 1,
            "secondary": 2,
            "success": 3,
            "danger": 4,
            "link": 5
        }
        return styles.get(style, 1)

    def create_roi_simulation_message(self, simulation_data: Dict) -> Dict:
        """
        Crea mensaje interactivo para simulación ROI

        Args:
            simulation_data: Output de stats_engine.calculate_roi_simulation()

        Returns:
            Dict con content, actions y embed listos para enviar
        """
        sku = simulation_data["sku"]
        name = simulation_data["name"]
        units = simulation_data["units"]
        roi_expected = simulation_data["roi_expected"]
        roi_range = simulation_data["roi_range"]
        investment = simulation_data["investment"]
        breakeven = simulation_data["breakeven_days"]
        risk_level = simulation_data["risk_level"]

        # Emoji según riesgo
        risk_emoji = {
            "bajo": "✅",
            "medio": "⚠️",
            "alto": "🔴"
        }

        # Content (texto principal)
        content = f"""🦈 **SIMULACIÓN ROI - {name}**

{risk_emoji[risk_level]} Riesgo: **{risk_level.upper()}**
💰 Inversión: **${investment:,.0f}**
📊 ROI: **{roi_expected:.1f}%** (85% confianza: {roi_range[0]:.1f}% - {roi_range[1]:.1f}%)
⏱️ Breakeven: **~{breakeven:.0f} días**"""

        # Actions (botones)
        actions = [
            {
                "label": f"✅ Aprobar {units} unidades",
                "style": "success",
                "action_id": f"approve_reorder_{sku}_{units}",
                "url": f"{os.getenv('BASE_URL', 'http://localhost:5000')}/api/execute-reorder?sku={sku}&units={units}"
            },
            {
                "label": "🔄 Simular Agresivo (+50%)",
                "style": "primary",
                "action_id": f"simulate_aggressive_{sku}",
                "url": f"{os.getenv('BASE_URL', 'http://localhost:5000')}/api/roi-simulator?sku={sku}&units={int(units * 1.5)}"
            },
            {
                "label": "❌ Rechazar",
                "style": "danger",
                "action_id": f"reject_{sku}"
            }
        ]

        # Agregar botón de freeze (solo si hay espacio - máx 5 botones)
        actions = self.add_freeze_button(actions)

        # Embed (formato rico)
        embed = {
            "title": f"🦈 {name} ({sku})",
            "color": 3066993 if risk_level == "bajo" else 15844367 if risk_level == "medio" else 15158332,
            "fields": [
                {
                    "name": "💰 Inversión",
                    "value": f"${investment:,.0f}",
                    "inline": True
                },
                {
                    "name": "📈 ROI Esperado",
                    "value": f"{roi_expected:.1f}%",
                    "inline": True
                },
                {
                    "name": "⏱️ Breakeven",
                    "value": f"{breakeven:.0f} días",
                    "inline": True
                },
                {
                    "name": "📊 Rango Confianza (85%)",
                    "value": f"{roi_range[0]:.1f}% - {roi_range[1]:.1f}%",
                    "inline": False
                }
            ],
            "footer": {
                "text": f"Simulación Monte Carlo • {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            }
        }

        return {
            "content": content,
            "actions": actions,
            "embed": embed
        }

    def create_liquidity_alert_message(self, shield_data: Dict) -> Dict:
        """
        Crea mensaje interactivo para alertas de liquidez

        Args:
            shield_data: Output de liquidity_guard.calculate_liquidity_shield()

        Returns:
            Dict con content, actions y embed
        """
        escudo_active = shield_data["escudo_active"]
        days_coverage = shield_data["days_of_coverage"]
        risk_level = shield_data["risk_level"]
        escudo_reserve = shield_data.get("escudo_reserve", 0)

        # Content
        if escudo_active:
            content = f"""🛡️ **ESCUDO ACTIVADO** - Protección de Liquidez

⚠️ Riesgo: **{risk_level.upper()}**
📊 Cobertura: **{days_coverage:.0f} días**
💰 Reserva sugerida: **${escudo_reserve:,.0f}**"""
        else:
            content = f"""✅ **LIQUIDEZ SALUDABLE**

📊 Cobertura: **{days_coverage:.0f} días**
🚀 Status: **{risk_level.upper()}**"""

        # Actions
        actions = []

        if escudo_active:
            actions.append({
                "label": "💀 Ver Dead Stock",
                "style": "secondary",
                "action_id": "view_dead_stock",
                "url": f"{os.getenv('BASE_URL', 'http://localhost:5000')}/api/cashflow/dead-stock"
            })
            actions.append({
                "label": "🔥 Liquidar Top 5",
                "style": "danger",
                "action_id": "liquidate_top5",
                "url": f"{os.getenv('BASE_URL', 'http://localhost:5000')}/api/execute-liquidate?top=5"
            })

        actions.append({
            "label": "📊 Ver Dashboard",
            "style": "primary",
            "action_id": "view_dashboard",
            "url": f"{os.getenv('BASE_URL', 'http://localhost:5000')}/dashboard"
        })

        # Embed
        ccc = shield_data.get("ccc_status", {})
        embed = {
            "title": "🛡️ Escudo de Liquidez" if escudo_active else "✅ Liquidez Saludable",
            "color": 15158332 if escudo_active else 3066993,
            "fields": [
                {
                    "name": "📊 Días de Cobertura",
                    "value": f"{days_coverage:.0f} días",
                    "inline": True
                },
                {
                    "name": "💰 Inventario",
                    "value": f"${shield_data['current_inventory_value']:,.0f}",
                    "inline": True
                },
                {
                    "name": "🔥 Burn Rate Diario",
                    "value": f"${shield_data['daily_burn_rate']:,.0f}",
                    "inline": True
                },
                {
                    "name": "🔄 CCC",
                    "value": f"{ccc.get('ccc_days', 'N/A')} días ({ccc.get('health', 'N/A')})",
                    "inline": False
                }
            ],
            "footer": {
                "text": f"Actualizado • {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            }
        }

        if escudo_active:
            embed["fields"].append({
                "name": "🛡️ Reserva Sugerida",
                "value": f"${escudo_reserve:,.0f} ({int(shield_data.get('escudo_reserve', 0) / shield_data.get('current_inventory_value', 1) * 100)}% del inventario)",
                "inline": False
            })

        # Agregar botón de freeze
        actions = self.add_freeze_button(actions)

        return {
            "content": content,
            "actions": actions,
            "embed": embed
        }

    def create_combined_action_message(
        self,
        simulation_data: Dict,
        shield_data: Dict
    ) -> Dict:
        """
        Crea mensaje combinado: ROI + Escudo con acciones combinadas

        Args:
            simulation_data: Datos de simulación ROI
            shield_data: Datos del escudo de liquidez

        Returns:
            Dict con content, actions y embed combinados
        """
        sku = simulation_data["sku"]
        name = simulation_data["name"]
        units = simulation_data["units"]
        roi = simulation_data["roi_expected"]
        escudo_active = shield_data["escudo_active"]
        days_coverage = shield_data["days_of_coverage"]

        # Content integrado
        content = f"""🦈🛡️ **ANÁLISIS COMPLETO - {name}**

**Simulación ROI:**
📊 ROI: {roi:.1f}% | ⏱️ Breakeven: {simulation_data['breakeven_days']:.0f} días

**Estado de Liquidez:**
{'🛡️ Escudo ACTIVO' if escudo_active else '✅ Liquidez OK'} | 📊 Cobertura: {days_coverage:.0f} días

**Recomendación:**
{self._generate_combined_recommendation(simulation_data, shield_data)}"""

        # Actions combinadas
        actions = []

        if escudo_active:
            # Acción combinada: Liquidar + Reordenar
            actions.append({
                "label": "🔥 Liquidar + Reordenar",
                "style": "success",
                "action_id": f"liquidate_and_reorder_{sku}_{units}",
                "url": f"{os.getenv('BASE_URL', 'http://localhost:5000')}/api/execute-combined?action=liquidate_reorder&sku={sku}&units={units}"
            })
        else:
            # Reordenar directo
            actions.append({
                "label": f"✅ Aprobar {units} unidades",
                "style": "success",
                "action_id": f"approve_{sku}_{units}",
                "url": f"{os.getenv('BASE_URL', 'http://localhost:5000')}/api/execute-reorder?sku={sku}&units={units}"
            })

        actions.extend([
            {
                "label": "📊 Ver Análisis Completo",
                "style": "primary",
                "action_id": "view_full_analysis",
                "url": f"{os.getenv('BASE_URL', 'http://localhost:5000')}/dashboard"
            },
            {
                "label": "❌ Rechazar",
                "style": "danger",
                "action_id": f"reject_{sku}"
            }
        ])

        # Embed combinado
        embed = {
            "title": f"🦈🛡️ {name} ({sku})",
            "color": 3447003,  # Azul
            "fields": [
                {
                    "name": "💰 Inversión",
                    "value": f"${simulation_data['investment']:,.0f}",
                    "inline": True
                },
                {
                    "name": "📈 ROI",
                    "value": f"{roi:.1f}%",
                    "inline": True
                },
                {
                    "name": "⏱️ Breakeven",
                    "value": f"{simulation_data['breakeven_days']:.0f} días",
                    "inline": True
                },
                {
                    "name": "🛡️ Estado Liquidez",
                    "value": "ESCUDO ACTIVO" if escudo_active else "Saludable",
                    "inline": True
                },
                {
                    "name": "📊 Cobertura",
                    "value": f"{days_coverage:.0f} días",
                    "inline": True
                },
                {
                    "name": "🔄 Riesgo",
                    "value": simulation_data['risk_level'].upper(),
                    "inline": True
                }
            ],
            "footer": {
                "text": f"Análisis Completo • {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            }
        }

        # Agregar botón de freeze
        actions = self.add_freeze_button(actions)

        return {
            "content": content,
            "actions": actions,
            "embed": embed
        }

    def _generate_combined_recommendation(
        self,
        simulation_data: Dict,
        shield_data: Dict
    ) -> str:
        """Genera recomendación combinada según datos"""

        roi = simulation_data["roi_expected"]
        escudo_active = shield_data["escudo_active"]
        risk_level = simulation_data["risk_level"]

        if escudo_active:
            if roi >= 30:
                return "🔥 ROI sólido pero Escudo activo. Liquidá dead stock primero y después dale gas."
            else:
                return "⚠️ ROI ajustado + Escudo activo. Peligroso - evaluá liquidar antes de invertir."
        else:
            if roi >= 30:
                return "✅ Liquidez OK + ROI fuerte. Move limpio - dale!"
            elif roi >= 15:
                return "⚡ Liquidez OK + ROI conservador. Proceder con cautela."
            else:
                return "🔴 ROI bajo. Mejor liquidar dead stock que invertir en esto."

    def create_price_surge_button(self, sku: str, surge_price: float, current_price: float) -> Dict:
        """
        Crea botón para activar Price Surge (precio dinámico).

        Args:
            sku: SKU del producto
            surge_price: Precio sugerido con surge
            current_price: Precio actual

        Returns:
            Dict con configuración del botón
        """
        surge_pct = ((surge_price - current_price) / current_price) * 100

        return {
            "label": f"💹 PRECIO +{surge_pct:.0f}% (48h)",
            "style": "primary",  # Azul
            "action_id": f"price_surge_{sku}",
            "url": f"{os.getenv('BASE_URL', 'http://localhost:5000')}/api/execute-price-surge",
            "metadata": {
                "sku": sku,
                "surge_price": surge_price,
                "duration_hours": 48
            }
        }

    def create_bundle_button(self, star_sku: str, dead_sku: str, bundle_price: float) -> Dict:
        """
        Crea botón para activar Parasite Bundle.

        Args:
            star_sku: SKU producto estrella
            dead_sku: SKU dead stock
            bundle_price: Precio del bundle

        Returns:
            Dict con configuración del botón
        """
        return {
            "label": f"📦 BUNDLE ${bundle_price:.0f}",
            "style": "success",  # Verde
            "action_id": f"bundle_{star_sku}_{dead_sku}",
            "url": f"{os.getenv('BASE_URL', 'http://localhost:5000')}/api/execute-bundle",
            "metadata": {
                "star_sku": star_sku,
                "dead_sku": dead_sku,
                "bundle_price": bundle_price,
                "duration_days": 7
            }
        }

    def add_freeze_button(self, actions: List[Dict]) -> List[Dict]:
        """
        Agrega botón de CONGELAR TODO a lista de acciones.

        IMPORTANTE: Discord limita a 5 botones por Action Row.
        Si ya hay 5 botones, no agregar (o crear nueva row).

        Args:
            actions: Lista existente de acciones

        Returns:
            Lista de acciones con botón freeze agregado
        """
        if len(actions) >= 5:
            # Ya hay 5 botones (límite Discord) - no agregar más
            return actions

        freeze_button = {
            "label": "❄️ CONGELAR TODO",
            "style": "danger",  # Rojo
            "action_id": "freeze_system_emergency",
            "url": f"{os.getenv('BASE_URL', 'http://localhost:5000')}/api/admin/freeze"
        }

        # Agregar al final
        actions.append(freeze_button)

        return actions

    def create_freeze_confirmation_message(self) -> Dict:
        """
        Crea mensaje de confirmación de congelamiento.

        Returns:
            Dict con content y embed para Discord
        """
        content = """❄️🔥 **PROTOCOLO CERO ABSOLUTO ACTIVADO**

🧊 **Sistema criogenizado**
🛡️ **Muro de fuego en Cash Flow**

**Estado:**
✅ Todos los endpoints de ejecución bloqueados
✅ Webhooks de salida invalidados
✅ Singularidad de Seguridad Preventiva registrada

**Acciones bloqueadas:**
- ❌ Reorden de productos
- ❌ Liquidaciones
- ❌ Acciones combinadas

**Para reactivar:** Usa /api/admin/thaw con X-Admin-Key"""

        embed = {
            "title": "❄️ PROTOCOLO CERO ABSOLUTO",
            "description": "Fer, sistema en modo seguro. Nada sale, nada entra hasta tu orden.",
            "color": 15158332,  # Rojo
            "fields": [
                {
                    "name": "🚨 Status",
                    "value": "FROZEN",
                    "inline": True
                },
                {
                    "name": "🔒 Nivel de Seguridad",
                    "value": "MÁXIMO",
                    "inline": True
                },
                {
                    "name": "⏰ Timestamp",
                    "value": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "inline": False
                }
            ],
            "footer": {
                "text": "Protocolo Cero Absoluto • Sistema de Emergencia"
            }
        }

        return {
            "content": content,
            "embed": embed
        }


# Testing simple
if __name__ == "__main__":
    handler = InteractiveHandler()

    # Test ROI message
    simulation_mock = {
        "sku": "SOMB-ARCO-09",
        "name": "Sombrero Arcoíris",
        "units": 25,
        "investment": 1500,
        "roi_expected": 60.5,
        "roi_range": [45.2, 75.8],
        "breakeven_days": 12.3,
        "risk_level": "bajo"
    }

    message = handler.create_roi_simulation_message(simulation_mock)

    print("\n" + "="*60)
    print("💬 MENSAJE INTERACTIVO - ROI")
    print("="*60)
    print(message["content"])
    print(f"\nBotones: {len(message['actions'])}")
    for action in message["actions"]:
        print(f"  - {action['label']}")
    print("="*60)
