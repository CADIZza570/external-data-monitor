# config_shared.py
"""
Configuración centralizada del proyecto.
Single Source of Truth para todos los scripts.
"""
import os
from dotenv import load_dotenv

# Cargar variables de entorno una sola vez
load_dotenv()

# =========================
# 🔐 SHOPIFY
# =========================
SHOPIFY_WEBHOOK_SECRET = os.getenv("SHOPIFY_WEBHOOK_SECRET", "dev_secret_key_change_in_production")
SHOPIFY_STORE = os.getenv("SHOPIFY_STORE", "tu-tienda.myshopify.com")
SHOPIFY_TOKEN = os.getenv("SHOPIFY_TOKEN", "")
SHOPIFY_API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2024-01")

# =========================
# ⚙️ THRESHOLDS & ALERTS
# =========================
LOW_STOCK_THRESHOLD = int(os.getenv("LOW_STOCK_THRESHOLD", 5))
NO_SALES_DAYS = int(os.getenv("NO_SALES_DAYS", 60))

# =========================
# 📧 EMAIL
# =========================
EMAIL_SMTP_SERVER = os.getenv("EMAIL_SMTP_SERVER", "smtp.hostinger.com")
EMAIL_SMTP_PORT = int(os.getenv("EMAIL_SMTP_PORT", 465))
EMAIL_SENDER = os.getenv("EMAIL_SENDER", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
EMAIL_RECIPIENTS = os.getenv("EMAIL_RECIPIENTS", "")

# =========================
# 🛠️ DEVELOPMENT
# =========================
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"

# =========================
# 📁 PATHS
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
LOG_DIR = os.path.join(BASE_DIR, "logs")
LOG_FILE = os.path.join(LOG_DIR, "webhook_server.log")

# Crear directorios si no existen
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# =========================
# ✅ VALIDACIÓN
# =========================
def validate_config(strict=False):
    """
    Valida que las variables críticas existan.
    
    Args:
        strict: Si es True, falla si faltan variables.
                Si es False, solo muestra warnings (para desarrollo).
    """
    missing = []
    
    if not SHOPIFY_WEBHOOK_SECRET or SHOPIFY_WEBHOOK_SECRET == "dev_secret_key_change_in_production":
        missing.append("SHOPIFY_WEBHOOK_SECRET")
    
    if not SHOPIFY_TOKEN:
        missing.append("SHOPIFY_TOKEN")
    
    if not EMAIL_SENDER:
        missing.append("EMAIL_SENDER")
    
    if not EMAIL_PASSWORD:
        missing.append("EMAIL_PASSWORD")
    
    if missing:
        warning_msg = (
            "⚠️  Missing optional environment variables:\n"
            + "\n".join(f"   - {var}" for var in missing)
            + "\n\n💡 App will run with defaults. Set these in Railway for production."
        )
        
        if strict:
            raise RuntimeError(
                "❌ Missing required environment variables:\n"
                + "\n".join(f"   - {var}" for var in missing)
                + "\n\n👉 Please check your .env file or Railway variables."
            )
        else:
            print(warning_msg)
    else:
        print("✅ All configuration variables loaded successfully")
    
    return True

# ✅ CAMBIO CRÍTICO: NO validar automáticamente al importar
# Esto permite que Railway inicie sin crashear si faltan variables
# webhook_server.py llamará validate_config(strict=False) manualmente