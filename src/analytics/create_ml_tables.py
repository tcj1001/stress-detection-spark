import re

import pymysql

from project_config import MYSQL_CONFIG


database_name = MYSQL_CONFIG['database']
if not re.fullmatch(r'[A-Za-z0-9_]+', database_name):
    raise ValueError('STRESS_DB_NAME may only contain letters, digits, and underscores')

server_config = {key: value for key, value in MYSQL_CONFIG.items() if key != 'database'}
with pymysql.connect(**server_config) as server_connection:
    with server_connection.cursor() as cursor:
        cursor.execute(
            f'CREATE DATABASE IF NOT EXISTS `{database_name}` '
            'DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci'
        )
    server_connection.commit()

table_statements = [
    """CREATE TABLE IF NOT EXISTS t_daily_stress (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id BIGINT,
        activity_date DATE,
        stress_score DECIMAL(5,2),
        risk_level VARCHAR(10),
        hr_score DECIMAL(5,2),
        sleep_score DECIMAL(5,2),
        active_score DECIMAL(5,2),
        sedentary_score DECIMAL(5,2),
        trend_label VARCHAR(20),
        score_7day_avg DECIMAL(5,2),
        INDEX idx_daily_user_date (user_id, activity_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS t_trend_analysis (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id BIGINT,
        activity_date DATE,
        stress_score DECIMAL(5,2),
        score_7day_avg DECIMAL(5,2),
        score_change_rate DECIMAL(8,4),
        trend_label VARCHAR(20),
        INDEX idx_trend_user_date (user_id, activity_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS t_correlation_matrix (
        id INT AUTO_INCREMENT PRIMARY KEY,
        feature_x VARCHAR(50),
        feature_y VARCHAR(50),
        corr_value DECIMAL(6,4)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS t_user_profile (
        user_id BIGINT PRIMARY KEY,
        cluster_id INT,
        cluster_label VARCHAR(20),
        avg_stress_score DECIMAL(5,2),
        avg_sleep_efficiency DECIMAL(5,4),
        avg_active_minutes DECIMAL(6,2),
        avg_resting_hr DECIMAL(5,2),
        avg_sedentary_ratio DECIMAL(5,4),
        risk_level VARCHAR(10)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS t_hourly_pattern (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id BIGINT,
        hour_of_day INT,
        avg_intensity DECIMAL(6,4),
        avg_calories DECIMAL(8,4),
        avg_steps DECIMAL(8,2),
        record_count INT,
        INDEX idx_hourly_user_hour (user_id, hour_of_day)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS t_classification_result (
        id INT AUTO_INCREMENT PRIMARY KEY,
        model_name VARCHAR(50),
        user_id BIGINT,
        activity_date DATE,
        actual_risk VARCHAR(10),
        predicted_risk VARCHAR(10),
        prediction_correct TINYINT,
        probability_high DECIMAL(6,4),
        probability_medium DECIMAL(6,4),
        probability_low DECIMAL(6,4),
        INDEX idx_classification_user_date (user_id, activity_date),
        INDEX idx_classification_model (model_name)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS t_feature_importance (
        id INT AUTO_INCREMENT PRIMARY KEY,
        model_name VARCHAR(50),
        feature_name VARCHAR(50),
        importance DECIMAL(10,6),
        rank_order INT
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS t_model_metrics (
        id INT AUTO_INCREMENT PRIMARY KEY,
        model_name VARCHAR(50),
        metric_name VARCHAR(50),
        metric_value DECIMAL(10,6)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS t_learning_curve (
        id INT AUTO_INCREMENT PRIMARY KEY,
        model_name VARCHAR(50),
        train_size INT,
        train_score DECIMAL(10,6),
        test_score DECIMAL(10,6)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
]

with pymysql.connect(**MYSQL_CONFIG) as connection:
    with connection.cursor() as cursor:
        for statement in table_statements:
            cursor.execute(statement)

        cursor.execute('SHOW TABLES')
        tables = [row[0] for row in cursor.fetchall()]
    connection.commit()

print(f'Database ready: {database_name}')
print(f'Tables available: {len(tables)}')
for table in tables:
    print(f'  {table}')
