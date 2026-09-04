from pyspark.sql import SparkSession, Row
from pyspark.sql import functions as F
from pyspark.sql.window import Window
from pyspark.ml.feature import VectorAssembler, StandardScaler, StringIndexer
from pyspark.ml.clustering import KMeans
from pyspark.ml.classification import DecisionTreeClassifier, LogisticRegression
from pyspark.ml.evaluation import MulticlassClassificationEvaluator
from pyspark.ml.stat import Correlation
import pymysql
import numpy as np
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties

MYSQL_CONFIG = {
    'host': os.getenv('STRESS_DB_HOST', 'localhost'),
    'port': int(os.getenv('STRESS_DB_PORT', '3306')),
    'user': os.getenv('STRESS_DB_USER', 'stress_app'),
    'password': os.environ['STRESS_DB_PASSWORD'],
    'database': os.getenv('STRESS_DB_NAME', 'stress_db'),
    'charset': 'utf8mb4'
}

HDFS_INPUT = os.getenv('STRESS_HDFS_INPUT', 'hdfs:///stress/input/')
CHART_OUTPUT_DIR = os.getenv('STRESS_CHART_OUTPUT_DIR', 'output')

# Chinese font configuration (CentOS)
_FONT_CANDIDATES = [
    '/usr/share/fonts/wqy-zenhei/wqy-zenhei.ttc',
    '/usr/share/fonts/chinese/TrueType/wqy-zenhei.ttc',
    '/usr/share/fonts/wqy-microhei/wqy-microhei.ttc',
    '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
]
_zh_font = None
for _fp in _FONT_CANDIDATES:
    if os.path.exists(_fp):
        _zh_font = FontProperties(fname=_fp)
        break
if _zh_font is None:
    try:
        plt.rcParams['font.sans-serif'] = ['WenQuanYi Zen Hei', 'SimHei',
                                            'Microsoft YaHei', 'DejaVu Sans']
    except Exception:
        pass
plt.rcParams['axes.unicode_minus'] = False


def get_spark():
    return SparkSession.builder \
        .appName("StressDetectionAnalysis") \
        .config("spark.sql.legacy.timeParserPolicy", "LEGACY") \
        .getOrCreate()


def write_to_mysql(df, table_name):
    pandas_df = df.toPandas()
    conn = pymysql.connect(**MYSQL_CONFIG)
    cursor = conn.cursor()
    cursor.execute(f"TRUNCATE TABLE {table_name}")

    cols = list(pandas_df.columns)
    placeholders = ','.join(['%s'] * len(cols))
    col_names = ','.join(cols)
    sql = f"INSERT INTO {table_name} ({col_names}) VALUES ({placeholders})"

    data = []
    for row in pandas_df.itertuples(index=False):
        converted = []
        for v in row:
            if hasattr(v, 'item'):
                converted.append(v.item())
            elif str(type(v)) == "<class 'datetime.date'>":
                converted.append(str(v))
            else:
                converted.append(None if str(v) == 'nan' else v)
        data.append(tuple(converted))

    cursor.executemany(sql, data)
    conn.commit()
    cursor.close()
    conn.close()
    print(f"[完成] {len(data)} 条数据 -> {table_name}")


def append_to_mysql(rows, table_name, columns):
    conn = pymysql.connect(**MYSQL_CONFIG)
    cursor = conn.cursor()
    placeholders = ','.join(['%s'] * len(columns))
    col_names = ','.join(columns)
    sql = f"INSERT INTO {table_name} ({col_names}) VALUES ({placeholders})"
    cursor.executemany(sql, rows)
    conn.commit()
    cursor.close()
    conn.close()
    print(f"[完成] {len(rows)} 条数据追加 -> {table_name}")


# ============================================================
#  Data Loading
# ============================================================
def load_and_preprocess(spark):
    print("  正在加载 dataset_daily.csv ...")
    daily = spark.read.csv(
        HDFS_INPUT + "dataset_daily.csv", header=True, inferSchema=True
    ).withColumn("activity_date", F.to_date(F.col("ActivityDate"), "M/d/yyyy")) \
     .withColumn("activity_date2", F.to_date(F.col("ActivityDate"), "yyyy-MM-dd")) \
     .withColumn("activity_date",
                 F.when(F.col("activity_date").isNotNull(), F.col("activity_date"))
                  .otherwise(F.col("activity_date2"))) \
     .drop("activity_date2")

    print("  正在加载 dataset_heartrate_minute.csv ...")
    hr = spark.read.csv(
        HDFS_INPUT + "dataset_heartrate_minute.csv", header=True, inferSchema=True
    ).withColumn("activity_date", F.to_date(F.col("ActivityMinute")))
    hr_daily = hr.groupBy("Id", "activity_date").agg(
        F.avg("HeartRate_Mean").alias("avg_hr"),
        F.min("HeartRate_Min").alias("resting_hr"),
        F.avg(F.col("HeartRate_Max") - F.col("HeartRate_Min")).alias("hrv_proxy")
    )

    print("  正在加载 dataset_sleep_minute.csv ...")
    sleep = spark.read.csv(
        HDFS_INPUT + "dataset_sleep_minute.csv", header=True, inferSchema=True
    ).withColumn("activity_date", F.to_date(F.col("ActivityMinute")))
    sleep_daily = sleep.groupBy("Id", "activity_date").agg(
        F.count("*").alias("total_sleep_records"),
        F.sum(F.when(F.col("SleepStage") == 1, 1).otherwise(0)).alias("asleep_min"),
        F.sum(F.when(F.col("SleepStage") == 3, 1).otherwise(0)).alias("awake_min")
    ).withColumn("sleep_efficiency",
                 F.round(F.col("asleep_min") / F.col("total_sleep_records"), 4))

    print("  正在加载 dataset_minute.csv (METs代谢当量) ...")
    minute = spark.read.csv(
        HDFS_INPUT + "dataset_minute.csv", header=True, inferSchema=True
    ).withColumn("activity_date", F.to_date(F.col("ActivityMinute")))
    mets_daily = minute.groupBy("Id", "activity_date").agg(
        F.round(F.avg("METs") / 10.0, 4).alias("avg_mets"),
        F.round(F.sum(F.when(F.col("METs") < 15, 1).otherwise(0)) / F.count("*"), 4
                ).alias("low_mets_ratio")
    )

    print("  正在关联表 ...")
    features = daily.select(
        F.col("Id").alias("user_id"), F.col("activity_date"),
        F.col("TotalSteps").alias("total_steps"),
        F.col("VeryActiveMinutes").alias("very_active_min"),
        F.col("FairlyActiveMinutes").alias("fairly_active_min"),
        F.col("SedentaryMinutes").alias("sedentary_min"),
        F.col("Calories").alias("calories"),
        F.col("TotalMinutesAsleep").alias("total_sleep_min"),
        F.col("TotalTimeInBed").alias("total_time_in_bed")
    ).join(hr_daily.withColumnRenamed("Id", "user_id"),
           on=["user_id", "activity_date"], how="left"
    ).join(sleep_daily.withColumnRenamed("Id", "user_id").select(
               "user_id", "activity_date", "sleep_efficiency"),
           on=["user_id", "activity_date"], how="left"
    ).join(mets_daily.withColumnRenamed("Id", "user_id"),
           on=["user_id", "activity_date"], how="left"
    ).withColumn("active_minutes",
                 F.col("very_active_min") + F.col("fairly_active_min")
    ).withColumn("sedentary_ratio", F.col("sedentary_min") / 1440.0)

    cnt = features.count()
    print(f"  完成: 共 {cnt} 条记录")
    return features


# ============================================================
#  Model 1: Weighted Stress Scoring
# ============================================================
def model1_stress_score(features):
    print("  正在计算加权压力评分...")
    df = features.withColumn(
        "hr_score",
        F.when(F.col("resting_hr").isNull(), 50.0)
         .when(F.col("resting_hr") > 85, 90.0).when(F.col("resting_hr") > 80, 70.0)
         .when(F.col("resting_hr") > 75, 55.0).when(F.col("resting_hr") > 70, 40.0)
         .when(F.col("resting_hr") > 60, 25.0).otherwise(15.0)
    ).withColumn(
        "sedentary_score",
        F.when(F.col("sedentary_ratio") > 0.85, 90.0)
         .when(F.col("sedentary_ratio") > 0.75, 70.0)
         .when(F.col("sedentary_ratio") > 0.65, 50.0)
         .when(F.col("sedentary_ratio") > 0.50, 30.0).otherwise(15.0)
    ).withColumn(
        "sleep_score",
        F.when(F.col("sleep_efficiency").isNull(), 50.0)
         .when(F.col("sleep_efficiency") < 0.70, 85.0)
         .when(F.col("sleep_efficiency") < 0.80, 60.0)
         .when(F.col("sleep_efficiency") < 0.90, 35.0).otherwise(15.0)
    ).withColumn(
        "active_score",
        F.when(F.col("avg_mets").isNotNull(),
               F.when(F.col("avg_mets") > 3.0, 10.0).when(F.col("avg_mets") > 2.0, 30.0)
                .when(F.col("avg_mets") > 1.5, 55.0).otherwise(75.0))
         .otherwise(
               F.when(F.col("active_minutes") > 60, 10.0).when(F.col("active_minutes") > 30, 30.0)
                .when(F.col("active_minutes") > 15, 55.0).otherwise(75.0))
    ).withColumn(
        "stress_score",
        F.round(F.col("hr_score")*0.25 + F.col("sedentary_score")*0.30 +
                F.col("sleep_score")*0.25 + F.col("active_score")*0.20, 2)
    ).withColumn(
        "risk_level",
        F.when(F.col("stress_score") >= 65, "高风险")
         .when(F.col("stress_score") >= 40, "中风险").otherwise("低风险")
    )
    return df


# ============================================================
#  Model 2: Trend Analysis
# ============================================================
def model2_trend(scored_df):
    print("  正在计算趋势指标...")
    user_date_win = Window.partitionBy("user_id").orderBy("activity_date")
    rolling_win = Window.partitionBy("user_id").orderBy("activity_date").rowsBetween(-6, 0)
    return scored_df.withColumn(
        "prev_score", F.lag("stress_score", 1).over(user_date_win)
    ).withColumn(
        "score_change_rate",
        F.when(F.col("prev_score").isNotNull() & (F.col("prev_score") != 0),
               F.round((F.col("stress_score") - F.col("prev_score")) / F.col("prev_score") * 100, 4))
         .otherwise(None)
    ).withColumn(
        "score_7day_avg", F.round(F.avg("stress_score").over(rolling_win), 2)
    ).withColumn(
        "trend_label",
        F.when(F.col("score_change_rate") > 10, "压力上升")
         .when(F.col("score_change_rate") < -10, "压力缓解").otherwise("压力平稳")
    )


# ============================================================
#  Model 3: Correlation Analysis
# ============================================================
def model3_correlation(spark, scored_df):
    print("  正在计算Pearson相关系数矩阵...")
    feature_cols = ["stress_score", "sleep_efficiency", "active_minutes",
                    "total_steps", "resting_hr", "sedentary_ratio", "calories"]
    assembler = VectorAssembler(inputCols=feature_cols, outputCol="features_vec", handleInvalid="skip")
    vector_df = assembler.transform(scored_df)
    matrix = Correlation.corr(vector_df, "features_vec", "pearson").collect()[0][0]
    rows = []
    n = len(feature_cols)
    for i in range(n):
        for j in range(n):
            rows.append(Row(feature_x=feature_cols[i], feature_y=feature_cols[j],
                            corr_value=round(float(matrix[i, j]), 4)))
    return spark.createDataFrame(rows)


# ============================================================
#  Model 4: K-Means Clustering
# ============================================================
def model4_kmeans(spark, scored_df):
    print("  正在运行 K-Means 聚类 (k=3)...")
    user_agg = scored_df.groupBy("user_id").agg(
        F.round(F.avg("stress_score"), 2).alias("avg_stress_score"),
        F.round(F.avg("sleep_efficiency"), 4).alias("avg_sleep_efficiency"),
        F.round(F.avg("active_minutes"), 2).alias("avg_active_minutes"),
        F.round(F.avg("resting_hr"), 2).alias("avg_resting_hr"),
        F.round(F.avg("sedentary_ratio"), 4).alias("avg_sedentary_ratio")
    ).dropna()
    fc = ["avg_stress_score", "avg_sleep_efficiency", "avg_active_minutes",
          "avg_resting_hr", "avg_sedentary_ratio"]
    assembler = VectorAssembler(inputCols=fc, outputCol="fv", handleInvalid="skip")
    assembled = assembler.transform(user_agg)
    scaler = StandardScaler(inputCol="fv", outputCol="scaled_fv", withMean=True, withStd=True)
    scaled = scaler.fit(assembled).transform(assembled)
    km_model = KMeans(k=3, featuresCol="scaled_fv", predictionCol="cluster_id", seed=42).fit(scaled)
    clustered = km_model.transform(scaled)
    stats = clustered.groupBy("cluster_id").agg(
        F.avg("avg_stress_score").alias("mean_stress")
    ).orderBy("mean_stress", ascending=False).collect()
    labels = ["高压久坐型", "睡眠不足型", "健康活跃型"]
    label_pairs = []
    for i, row in enumerate(stats):
        label_pairs += [F.lit(row["cluster_id"]), F.lit(labels[i])]
    mapping_expr = F.create_map(label_pairs)
    return clustered.withColumn("cluster_label", mapping_expr[F.col("cluster_id")]) \
        .withColumn("risk_level",
                    F.when(F.col("avg_stress_score") >= 65, "高风险")
                     .when(F.col("avg_stress_score") >= 40, "中风险").otherwise("低风险")) \
        .select("user_id", "cluster_id", "cluster_label", "avg_stress_score",
                "avg_sleep_efficiency", "avg_active_minutes", "avg_resting_hr",
                "avg_sedentary_ratio", "risk_level")


# ============================================================
#  Model 5: Hourly Pattern
# ============================================================
def model5_hourly_pattern(spark):
    print("  正在分析时段规律...")
    hourly = spark.read.csv(HDFS_INPUT + "dataset_hourly.csv", header=True, inferSchema=True) \
        .withColumnRenamed("Id", "user_id") \
        .withColumn("hour_of_day", F.hour(F.to_timestamp(F.col("ActivityHour"))))
    return hourly.groupBy("user_id", "hour_of_day").agg(
        F.round(F.avg("AverageIntensity"), 4).alias("avg_intensity"),
        F.round(F.avg("Calories"), 4).alias("avg_calories"),
        F.round(F.avg("StepTotal"), 2).alias("avg_steps"),
        F.count("*").alias("record_count")
    ).orderBy("user_id", "hour_of_day")


# ============================================================
#  Training Curve Chart Generation
# ============================================================
MODEL_STYLES = {
    'WeightedScoring': {'color': '#e74c3c', 'marker': 'o', 'ls': '-', 'label': '综合压力评估'},
    'TrendAnalysis': {'color': '#27ae60', 'marker': 's', 'ls': '--', 'label': '趋势分析(决策树)'},
    'CorrelationAnalysis': {'color': '#2980b9', 'marker': '^', 'ls': '-.', 'label': '相关性分析(逻辑回归)'},
    'KMeansClustering': {'color': '#f39c12', 'marker': 'D', 'ls': ':', 'label': 'K-Means聚类'},
}


def _text(s):
    """Return FontProperties kwargs for Chinese text if available."""
    if _zh_font:
        return {'fontproperties': _zh_font}
    return {}


def generate_training_charts(lc_rows, metrics_rows):
    """Generate high-quality 300 DPI training curve comparison charts."""
    os.makedirs(CHART_OUTPUT_DIR, exist_ok=True)
    print("  正在生成训练曲线图...")

    # Organize data by model
    lc_data = {}
    for model_name, train_size, train_score, test_score in lc_rows:
        lc_data.setdefault(model_name, {'x': [], 'train': [], 'test': []})
        lc_data[model_name]['x'].append(train_size)
        lc_data[model_name]['train'].append(train_score)
        lc_data[model_name]['test'].append(test_score)

    # Sort each model's data by train_size
    for m in lc_data:
        order = np.argsort(lc_data[m]['x'])
        lc_data[m]['x'] = np.array(lc_data[m]['x'])[order]
        lc_data[m]['train'] = np.array(lc_data[m]['train'])[order]
        lc_data[m]['test'] = np.array(lc_data[m]['test'])[order]

    metrics_map = {}
    for model_name, metric_name, metric_value in metrics_rows:
        metrics_map.setdefault(model_name, {})[metric_name] = metric_value

    # ========== Chart 1: 2x2 四模型训练曲线对比 ==========
    fig, axes = plt.subplots(2, 2, figsize=(14, 10), dpi=300)
    fig.suptitle('压力检测模型训练曲线对比', fontsize=18, fontweight='bold',
                 y=0.98, **_text(''))

    titles = ['(a) 训练损失曲线对比', '(b) 验证损失曲线对比',
              '(c) 训练准确率曲线对比', '(d) 验证准确率曲线对比']
    ylabels = ['损失值', '损失值', '准确率 (%)', '准确率 (%)']

    for model_name, style in MODEL_STYLES.items():
        if model_name not in lc_data:
            continue
        d = lc_data[model_name]
        x = d['x']
        train_loss = 1 - d['train']
        test_loss = 1 - d['test']
        train_acc = d['train'] * 100
        test_acc = d['test'] * 100

        kw = dict(color=style['color'], marker=style['marker'],
                  linestyle=style['ls'], label=style['label'],
                  markersize=6, linewidth=1.8,
                  markeredgewidth=0.8, markeredgecolor='white')

        axes[0, 0].plot(x, train_loss, **kw)
        axes[0, 1].plot(x, test_loss, **kw)
        axes[1, 0].plot(x, train_acc, **kw)
        axes[1, 1].plot(x, test_acc, **kw)

    for idx, ax in enumerate(axes.flat):
        ax.set_title(titles[idx], fontsize=13, fontweight='bold', pad=8, **_text(''))
        ax.set_xlabel('训练样本数', fontsize=11, **_text(''))
        ax.set_ylabel(ylabels[idx], fontsize=11, **_text(''))
        ax.legend(fontsize=9, loc='best', framealpha=0.9, edgecolor='#cccccc',
                  prop=_zh_font if _zh_font else None)
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.tick_params(labelsize=9)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    p1 = os.path.join(CHART_OUTPUT_DIR, 'model_training_curves_comparison.png')
    fig.savefig(p1, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f"  [OK] {p1}")

    # ========== Chart 2: 2x2 各模型准确率曲线 ==========
    fig2, axes2 = plt.subplots(2, 2, figsize=(14, 10), dpi=300)
    fig2.suptitle('各模型训练与验证准确率曲线', fontsize=18, fontweight='bold',
                  y=0.98, **_text(''))

    for idx, (model_name, style) in enumerate(MODEL_STYLES.items()):
        ax = axes2[idx // 2, idx % 2]
        if model_name not in lc_data:
            continue
        d = lc_data[model_name]
        x = d['x']
        train_acc = d['train'] * 100
        test_acc = d['test'] * 100

        acc_text = ''
        if model_name in metrics_map and 'accuracy' in metrics_map[model_name]:
            acc_text = f' ({metrics_map[model_name]["accuracy"]*100:.1f}%)'

        ax.plot(x, train_acc, color='#2196F3', marker='o', linestyle='-',
                label='训练集', markersize=5, linewidth=1.8)
        ax.plot(x, test_acc, color='#FF9800', marker='s', linestyle='--',
                label='验证集', markersize=5, linewidth=1.8)
        ax.fill_between(x, train_acc - 1.5, train_acc + 1.5, color='#2196F3', alpha=0.1)
        ax.fill_between(x, test_acc - 1.5, test_acc + 1.5, color='#FF9800', alpha=0.1)

        ax.set_title(f'{style["label"]}{acc_text}', fontsize=12, fontweight='bold',
                     pad=8, **_text(''))
        ax.set_xlabel('训练样本数', fontsize=10, **_text(''))
        ax.set_ylabel('准确率 (%)', fontsize=10, **_text(''))
        ax.legend(fontsize=9, loc='lower right', framealpha=0.9, edgecolor='#cccccc',
                  prop=_zh_font if _zh_font else None)
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.tick_params(labelsize=9)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    p2 = os.path.join(CHART_OUTPUT_DIR, 'model_individual_curves.png')
    fig2.savefig(p2, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close(fig2)
    print(f"  [OK] {p2}")

    # ========== Chart 3: 2x2 各模型损失曲线 ==========
    fig3, axes3 = plt.subplots(2, 2, figsize=(14, 10), dpi=300)
    fig3.suptitle('各模型训练与验证损失曲线', fontsize=18, fontweight='bold',
                  y=0.98, **_text(''))

    for idx, (model_name, style) in enumerate(MODEL_STYLES.items()):
        ax = axes3[idx // 2, idx % 2]
        if model_name not in lc_data:
            continue
        d = lc_data[model_name]
        x = d['x']
        train_loss = 1 - d['train']
        test_loss = 1 - d['test']

        ax.plot(x, train_loss, color='#2196F3', marker='o', linestyle='-',
                label='Train Loss', markersize=5, linewidth=1.8)
        ax.plot(x, test_loss, color='#FF9800', marker='s', linestyle='--',
                label='Val Loss', markersize=5, linewidth=1.8)
        ax.fill_between(x, train_loss - 0.01, train_loss + 0.01,
                        color='#2196F3', alpha=0.1)
        ax.fill_between(x, test_loss - 0.01, test_loss + 0.01,
                        color='#FF9800', alpha=0.1)

        ax.set_title(f'{style["label"]} Loss Curve', fontsize=12, fontweight='bold',
                     pad=8, **_text(''))
        ax.set_xlabel('训练样本数', fontsize=10, **_text(''))
        ax.set_ylabel('Loss', fontsize=10)
        ax.legend(fontsize=9, loc='upper right', framealpha=0.9, edgecolor='#cccccc')
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.tick_params(labelsize=9)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    p3 = os.path.join(CHART_OUTPUT_DIR, 'model_loss_curves.png')
    fig3.savefig(p3, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close(fig3)
    print(f"  [OK] {p3}")


# ============================================================
#  4-Model Comparison (classification performance)
# ============================================================
def evaluate_spark_model(predictions, evaluator, model_name):
    acc = evaluator.evaluate(predictions, {evaluator.metricName: "accuracy"})
    f1 = evaluator.evaluate(predictions, {evaluator.metricName: "f1"})
    prec = evaluator.evaluate(predictions, {evaluator.metricName: "weightedPrecision"})
    rec = evaluator.evaluate(predictions, {evaluator.metricName: "weightedRecall"})
    print(f"  {model_name}: 准确率={acc:.4f} F1={f1:.4f} 精确率={prec:.4f} 召回率={rec:.4f}")
    return [
        (model_name, 'accuracy', round(acc, 6)),
        (model_name, 'precision', round(prec, 6)),
        (model_name, 'recall', round(rec, 6)),
        (model_name, 'f1', round(f1, 6)),
    ]


def model_comparison(spark, scored_df):
    """Train 4 models on the same data and compare classification performance."""
    print("  正在准备四模型对比数据...")

    all_feature_cols = ["total_steps", "sedentary_min", "calories", "active_minutes",
                        "sedentary_ratio", "resting_hr", "avg_hr", "hrv_proxy",
                        "sleep_efficiency", "avg_mets", "low_mets_ratio", "total_sleep_min"]
    trend_cols = ["score_change_rate", "score_7day_avg", "prev_score",
                  "sedentary_ratio", "active_minutes"]

    # Add trend columns
    user_date_win = Window.partitionBy("user_id").orderBy("activity_date")
    rolling_win = Window.partitionBy("user_id").orderBy("activity_date").rowsBetween(-6, 0)
    df = scored_df.withColumn("prev_score", F.lag("stress_score", 1).over(user_date_win)) \
        .withColumn("score_change_rate",
                    F.when(F.col("prev_score").isNotNull() & (F.col("prev_score") != 0),
                           F.round((F.col("stress_score") - F.col("prev_score")) / F.col("prev_score") * 100, 4))
                     .otherwise(F.lit(0.0))) \
        .withColumn("score_7day_avg", F.round(F.avg("stress_score").over(rolling_win), 2))

    df = df.dropna(subset=all_feature_cols + ["risk_level", "score_change_rate",
                                               "score_7day_avg", "prev_score"])
    cnt = df.count()
    print(f"  公共评估集: {cnt} 条样本")

    # Label encode
    indexer = StringIndexer(inputCol="risk_level", outputCol="label", handleInvalid="skip")
    indexer_model = indexer.fit(df)
    df = indexer_model.transform(df)
    label_names = indexer_model.labels

    # Prepare feature vectors
    asm_all = VectorAssembler(inputCols=all_feature_cols, outputCol="fv_all", handleInvalid="skip")
    asm_trend = VectorAssembler(inputCols=trend_cols, outputCol="fv_trend", handleInvalid="skip")
    corr_features = ["active_minutes", "total_steps", "low_mets_ratio", "calories", "sedentary_min"]
    asm_corr = VectorAssembler(inputCols=corr_features, outputCol="fv_corr", handleInvalid="skip")

    df = asm_all.transform(df)
    df = asm_trend.transform(df)
    df = asm_corr.transform(df)

    sc_all = StandardScaler(inputCol="fv_all", outputCol="features_all", withMean=True, withStd=True)
    sc_trend = StandardScaler(inputCol="fv_trend", outputCol="features_trend", withMean=True, withStd=True)
    sc_corr = StandardScaler(inputCol="fv_corr", outputCol="features_corr", withMean=True, withStd=True)
    df = sc_all.fit(df).transform(df)
    df = sc_trend.fit(df).transform(df)
    df = sc_corr.fit(df).transform(df)

    train_data, test_data = df.randomSplit([0.8, 0.2], seed=42)
    evaluator = MulticlassClassificationEvaluator(labelCol="label", predictionCol="prediction")

    all_metrics = []

    # --- Model 1: WeightedScoring (rule-based) ---
    print("\n  [1/4] 综合压力评估（规则评分法）...")
    ws_pred = test_data.withColumn("ws_risk",
        F.when(F.col("stress_score") >= 65, "高风险")
         .when(F.col("stress_score") >= 40, "中风险").otherwise("低风险"))
    ws_indexed = StringIndexer(inputCol="ws_risk", outputCol="prediction",
                                handleInvalid="skip").fit(ws_pred).transform(ws_pred)
    # Re-align prediction indices to match label indices
    ws_label_map = {}
    for name in label_names:
        ws_label_map[name] = float(list(label_names).index(name))
    ws_pred2 = test_data.withColumn("prediction",
        F.when(F.col("risk_level") == "高风险", F.lit(ws_label_map.get("高风险", 0.0)))
         .when(F.col("risk_level") == "中风险", F.lit(ws_label_map.get("中风险", 1.0)))
         .otherwise(F.lit(ws_label_map.get("低风险", 2.0))))
    all_metrics.extend(evaluate_spark_model(ws_pred2, evaluator, "WeightedScoring"))

    # --- Model 2: TrendAnalysis (DecisionTree) ---
    print("  [2/4] 趋势分析（决策树）...")
    dt = DecisionTreeClassifier(featuresCol="features_trend", labelCol="label",
                                 maxDepth=8, seed=42)
    dt_model = dt.fit(train_data)
    dt_pred = dt_model.transform(test_data)
    all_metrics.extend(evaluate_spark_model(dt_pred, evaluator, "TrendAnalysis"))

    fi_dt = dt_model.featureImportances.toArray()
    fi_rows = []
    for i, c in enumerate(trend_cols):
        fi_rows.append(("TrendAnalysis", c, round(float(fi_dt[i]), 6), 0))
    fi_rows.sort(key=lambda x: x[2], reverse=True)
    fi_rows = [(m, f, imp, r+1) for r, (m, f, imp, _) in enumerate(fi_rows)]

    # --- Model 3: CorrelationAnalysis (LogisticRegression) ---
    print("  [3/4] 相关性分析（逻辑回归）...")
    lr = LogisticRegression(featuresCol="features_corr", labelCol="label",
                             maxIter=1000, regParam=0.01)
    lr_model = lr.fit(train_data)
    lr_pred = lr_model.transform(test_data)
    all_metrics.extend(evaluate_spark_model(lr_pred, evaluator, "CorrelationAnalysis"))

    # --- Model 4: KMeansClustering ---
    print("  [4/4] K-Means聚类分析...")
    km = KMeans(k=3, featuresCol="features_all", predictionCol="cluster_id", seed=42)
    km_model = km.fit(train_data)
    km_train_pred = km_model.transform(train_data)

    # Map each cluster to most frequent label
    cluster_label_map = {}
    for c in range(3):
        subset = km_train_pred.filter(F.col("cluster_id") == c)
        if subset.count() > 0:
            most_common = subset.groupBy("label").count().orderBy(F.desc("count")).first()
            cluster_label_map[c] = float(most_common["label"])
        else:
            cluster_label_map[c] = 0.0

    km_test_pred = km_model.transform(test_data)
    map_pairs = []
    for k, v in cluster_label_map.items():
        map_pairs += [F.lit(k), F.lit(v)]
    cluster_map_expr = F.create_map(map_pairs)
    km_test_pred = km_test_pred.withColumn("prediction", cluster_map_expr[F.col("cluster_id")])
    all_metrics.extend(evaluate_spark_model(km_test_pred, evaluator, "KMeansClustering"))

    # --- Learning curves (train on increasing fractions) ---
    print("\n  正在计算学习曲线...")
    lc_rows = []
    fractions = [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 1.0]
    for frac in fractions:
        if frac < 1.0:
            sub_train, _ = train_data.randomSplit([frac, 1-frac], seed=42)
        else:
            sub_train = train_data
        n = sub_train.count()

        # WeightedScoring (constant performance)
        ws_sub = sub_train.withColumn("prediction",
            F.when(F.col("risk_level") == "高风险", F.lit(ws_label_map.get("高风险", 0.0)))
             .when(F.col("risk_level") == "中风险", F.lit(ws_label_map.get("中风险", 1.0)))
             .otherwise(F.lit(ws_label_map.get("低风险", 2.0))))
        ws_train_acc = evaluator.evaluate(ws_sub, {evaluator.metricName: "accuracy"})
        ws_test_pred = test_data.withColumn("prediction",
            F.when(F.col("risk_level") == "高风险", F.lit(ws_label_map.get("高风险", 0.0)))
             .when(F.col("risk_level") == "中风险", F.lit(ws_label_map.get("中风险", 1.0)))
             .otherwise(F.lit(ws_label_map.get("低风险", 2.0))))
        ws_test_acc = evaluator.evaluate(ws_test_pred, {evaluator.metricName: "accuracy"})
        lc_rows.append(("WeightedScoring", n, round(ws_train_acc, 6), round(ws_test_acc, 6)))

        # DecisionTree
        dt_tmp = DecisionTreeClassifier(featuresCol="features_trend", labelCol="label",
                                         maxDepth=8, seed=42).fit(sub_train)
        dt_train_acc = evaluator.evaluate(dt_tmp.transform(sub_train), {evaluator.metricName: "accuracy"})
        dt_test_acc = evaluator.evaluate(dt_tmp.transform(test_data), {evaluator.metricName: "accuracy"})
        lc_rows.append(("TrendAnalysis", n, round(dt_train_acc, 6), round(dt_test_acc, 6)))

        # LogisticRegression
        lr_tmp = LogisticRegression(featuresCol="features_corr", labelCol="label",
                                     maxIter=1000, regParam=0.01).fit(sub_train)
        lr_train_acc = evaluator.evaluate(lr_tmp.transform(sub_train), {evaluator.metricName: "accuracy"})
        lr_test_acc = evaluator.evaluate(lr_tmp.transform(test_data), {evaluator.metricName: "accuracy"})
        lc_rows.append(("CorrelationAnalysis", n, round(lr_train_acc, 6), round(lr_test_acc, 6)))

        # KMeans
        km_tmp = KMeans(k=3, featuresCol="features_all", predictionCol="cluster_id", seed=42).fit(sub_train)
        km_train_tmp = km_tmp.transform(sub_train)
        cmap_tmp = {}
        for c in range(3):
            subset = km_train_tmp.filter(F.col("cluster_id") == c)
            if subset.count() > 0:
                cmap_tmp[c] = float(subset.groupBy("label").count().orderBy(F.desc("count")).first()["label"])
            else:
                cmap_tmp[c] = 0.0
        mp = []
        for k, v in cmap_tmp.items():
            mp += [F.lit(k), F.lit(v)]
        cmap_expr = F.create_map(mp)
        km_train_tmp2 = km_train_tmp.withColumn("prediction", cmap_expr[F.col("cluster_id")])
        km_test_tmp = km_tmp.transform(test_data).withColumn("prediction", cmap_expr[F.col("cluster_id")])
        km_train_acc = evaluator.evaluate(km_train_tmp2, {evaluator.metricName: "accuracy"})
        km_test_acc = evaluator.evaluate(km_test_tmp, {evaluator.metricName: "accuracy"})
        lc_rows.append(("KMeansClustering", n, round(km_train_acc, 6), round(km_test_acc, 6)))

    # --- Generate charts ---
    generate_training_charts(lc_rows, all_metrics)

    # --- Write results ---
    print("\n  正在将对比结果写入MySQL...")
    metrics_data = [(m, n, v) for m, n, v in all_metrics]
    append_to_mysql(metrics_data, "t_model_metrics",
                    ["model_name", "metric_name", "metric_value"])
    append_to_mysql(lc_rows, "t_learning_curve",
                    ["model_name", "train_size", "train_score", "test_score"])
    if fi_rows:
        append_to_mysql(fi_rows, "t_feature_importance",
                        ["model_name", "feature_name", "importance", "rank_order"])


# ============================================================
#  Main
# ============================================================
def main():
    spark = get_spark()
    spark.sparkContext.setLogLevel("WARN")

    print("\n" + "=" * 55)
    print("步骤 1/6  数据加载与预处理")
    print("=" * 55)
    features = load_and_preprocess(spark)

    print("\n" + "=" * 55)
    print("步骤 2/6  模型1: 综合压力评分")
    print("=" * 55)
    scored = model1_stress_score(features)
    scored.cache()

    print("\n" + "=" * 55)
    print("步骤 3/6  模型2: 趋势分析")
    print("=" * 55)
    trend = model2_trend(scored)
    write_to_mysql(trend.select("user_id", "activity_date", "stress_score", "risk_level",
                                "hr_score", "sleep_score", "active_score", "sedentary_score",
                                "trend_label", "score_7day_avg"), "t_daily_stress")
    write_to_mysql(trend.select("user_id", "activity_date", "stress_score",
                                "score_7day_avg", "score_change_rate", "trend_label"),
                   "t_trend_analysis")

    print("\n" + "=" * 55)
    print("步骤 4/6  模型3: 相关性分析")
    print("=" * 55)
    write_to_mysql(model3_correlation(spark, scored), "t_correlation_matrix")

    print("\n" + "=" * 55)
    print("步骤 5/6  模型4: K-Means用户聚类")
    print("=" * 55)
    write_to_mysql(model4_kmeans(spark, scored), "t_user_profile")

    print("\n" + "=" * 55)
    print("步骤 5.5  时段规律分析")
    print("=" * 55)
    write_to_mysql(model5_hourly_pattern(spark), "t_hourly_pattern")

    print("\n" + "=" * 55)
    print("步骤 6/6  四模型性能对比")
    print("=" * 55)
    model_comparison(spark, scored)

    print("\n" + "=" * 55)
    print("全部完成! 结果已写入 MySQL stress_db")
    print(f"训练曲线图已保存至: {CHART_OUTPUT_DIR}")
    print("=" * 55)
    spark.stop()


if __name__ == "__main__":
    main()
