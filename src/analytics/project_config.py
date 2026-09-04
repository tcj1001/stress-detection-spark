import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.getenv('STRESS_DATA_DIR', PROJECT_ROOT / 'data' / 'raw')).resolve()

MYSQL_CONFIG = {
    'host': os.getenv('STRESS_DB_HOST', 'localhost'),
    'port': int(os.getenv('STRESS_DB_PORT', '3306')),
    'user': os.getenv('STRESS_DB_USER', 'stress_app'),
    'password': os.environ['STRESS_DB_PASSWORD'],
    'database': os.getenv('STRESS_DB_NAME', 'stress_db'),
    'charset': 'utf8mb4',
}
