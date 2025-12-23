def fetch_data_api() -> pd.DataFrame:
    """
    Obtiene datos desde la API.
    """
    print("🌐 Conectando a la API...")
    logging.info("Conectando a la API")

    session = create_session()

    try:
        response = session.get(API_URL, timeout=10)
        response.raise_for_status()

        data = response.json()
        df = pd.DataFrame(data)

        print(f"✅ Datos obtenidos: {len(df)} registros")
        return df

    except RequestException as e:
        logging.error(str(e))
        raise RuntimeError("❌ Error al consultar la API")



def fetch_data_shopify() -> pd.DataFrame:
    """
    Descarga productos y variantes desde Shopify
    con paginación y los normaliza al formato del pipeline:
    product_id | name | stock
    """
    print("🛒 Conectando a Shopify API con paginación...")
    logging.info("Conectando a Shopify API")

    session = create_session()
    url = f"https://{SHOPIFY_STORE}/admin/api/{SHOPIFY_API_VERSION}/products.json?limit=250"
    headers = {"X-Shopify-Access-Token": SHOPIFY_TOKEN, "Content-Type": "application/json"}

    rows = []
    while url:
        try:
            response = session.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            data = response.json()
            products = data.get("products", [])

            for product in products:
                for variant in product.get("variants", []):
                    rows.append({
                        "product_id": variant.get("id"),
                        "name": f"{product.get('title')} - {variant.get('title')}",
                        "stock": variant.get("inventory_quantity")
                    })

            # Revisar si hay siguiente página
            link_header = response.headers.get("Link")
            if link_header and 'rel="next"' in link_header:
                # Extraer URL siguiente página
                import re
                match = re.search(r'<([^>]+)>; rel="next"', link_header)
                url = match.group(1) if match else None
            else:
                url = None

        except RequestException as e:
            logging.error(str(e))
            raise RuntimeError("❌ Error al consultar Shopify API")

    df = pd.DataFrame(rows)
    print(f"✅ Productos Shopify descargados: {len(df)} variantes")
    return df




def fetch_data_local(path: str) -> pd.DataFrame:
    """
    Carga un CSV local para pruebas manuales.
    """
    print(f"📂 Usando CSV local: {path}")

    if not os.path.exists(path):
        raise FileNotFoundError(f"❌ Archivo no encontrado: {path}")

    df = pd.read_csv(path)
    print(f"✅ Archivo cargado ({len(df)} filas)")
    return df




def create_session():
    """
    Crea una sesión HTTP con reintentos automáticos.
    """
    session = requests.Session()

    retries = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504]
    )

    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)

    return session




def process_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpieza y detección de duplicados.
    ⚠️ IMPORTANTE: usamos subset para evitar dicts.
    También elimina columnas pesadas y solo deja útiles según tipo de CSV.
    """
    print("\n📊 Iniciando procesamiento de datos...")

    original_count = len(df)

    if "stock" in df.columns:
        # CSV de productos
        duplicated_rows = df[df.duplicated(subset=["product_id"])]
        keep_cols = ["product_id", "name", "stock"]
    else:
        # CSV de usuarios
        duplicated_rows = df[df.duplicated(subset=["email"])]
        keep_cols = ["id", "name", "username", "email", "phone", "website", "city"]
        # Extraer ciudad si existe
        if "address" in df.columns:
            def extract_city(addr):
                if isinstance(addr, dict):
                    return addr.get("city", None)
                try:
                    return json.loads(addr.replace("'", '"')).get("city", None)
                except:
                    return None
            df.loc[:, "city"] = df["address"].apply(extract_city)

    if not duplicated_rows.empty:
        alert_msg = f"🚨 ALERTA: {len(duplicated_rows)} duplicados detectados"
        print(alert_msg)
        print(duplicated_rows[keep_cols])
        logging.warning(alert_msg)
    else:
        print("ℹ️ No se detectaron duplicados")

    df_clean = df[keep_cols].drop_duplicates()
    final_count = len(df_clean)

    print(f"Registros originales: {original_count}")
    print(f"Registros limpios: {final_count}")
    print(f"Duplicados eliminados: {original_count - final_count}")

    return df_clean




def save_raw(df: pd.DataFrame, ts: str):
    """
    Guarda CSV y JSON originales.
    """
    if "stock" in df.columns:
        csv_path = f"{OUTPUT_DIR}/products_data_{ts}.csv"
        json_path = f"{OUTPUT_DIR}/products_data_{ts}.json"
    else:
        csv_path = f"{OUTPUT_DIR}/users_data_{ts}.csv"
        json_path = f"{OUTPUT_DIR}/users_data_{ts}.json"

    df.to_csv(csv_path, index=False)
    df.to_json(json_path, orient="records", indent=2)

    print(f"💾 CSV guardado: {csv_path}")
    print(f"💾 JSON guardado: {json_path}")




def save_clean(df: pd.DataFrame, ts: str):
    """
    Guarda CSV limpio versionado.
    """
    if "stock" in df.columns:
        path = f"{OUTPUT_DIR}/products_data_{ts}_clean.csv"
    else:
        path = f"{OUTPUT_DIR}/users_data_{ts}_clean.csv"

    df.to_csv(path, index=False)
    print(f"✅ CSV limpio guardado: {path}")




def validate_data(df: pd.DataFrame):
    """
    Validación mínima de columnas críticas según tipo de CSV.
    """
    print("🔍 Validando estructura de datos...")

    if "stock" in df.columns:
        # CSV de productos
        required = {"product_id", "name", "stock"}
    else:
        # CSV de usuarios
        required = {"id", "name", "email"}

    if not required.issubset(df.columns):
        raise ValueError(f"❌ Faltan columnas requeridas para el tipo de CSV ({required})")

    print("✅ Validación exitosa")



