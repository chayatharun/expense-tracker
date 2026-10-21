
import os
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent


def get_db_connection():
    host = os.getenv("DB_HOST")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    database = os.getenv("DB_NAME")
    port = int(os.getenv("DB_PORT", "3306"))

    required = {
        "DB_HOST": host,
        "DB_USER": user,
        "DB_PASSWORD": password,
        "DB_NAME": database,
    }
    missing = [key for key, value in required.items() if not value]
    if missing:
        raise RuntimeError(
            "Missing database environment variables: "
            + ", ".join(missing)
        )

    config = {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "database": database,
        "connection_timeout": 15,
    }

    # Aiven requires TLS. Verify the server certificate when the
    # Aiven CA certificate is available.
    ssl_ca_setting = os.getenv("DB_SSL_CA", "ca.pem").strip()
    ssl_ca_path = Path(ssl_ca_setting)

    if not ssl_ca_path.is_absolute():
        ssl_ca_path = BASE_DIR / ssl_ca_path

    if ssl_ca_path.is_file():
        config.update({
            "ssl_ca": str(ssl_ca_path),
            "ssl_verify_cert": True,
            "ssl_verify_identity": True,
        })
    else:
        # Require encrypted TLS if no CA file has been configured.
        # For production, configure DB_SSL_CA with Aiven's CA file
        # so the server certificate and hostname can be verified.
        config["ssl_disabled"] = False

    return mysql.connector.connect(**config)
