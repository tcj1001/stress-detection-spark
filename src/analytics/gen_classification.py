"""
生成四模型分类预测数据（增强版），写入 t_classification_result
改进：
  1. 覆盖全部943条记录（缺失特征用中位数填充）
  2. 监督模型使用 5折交叉验证，避免训练集=测试集导致100%准确率
  3. 三个风险等级全部保留
"""
import pandas as pd
import numpy as np
import pymysql
from project_config import DATA_DIR, MYSQL_CONFIG
from sklearn.tree import DecisionTreeClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.cluster import KMeans
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import cross_val_predict

def calc_stress(row):
    hr_s = 50.0
    if pd.notna(row.get('resting_hr')):
        rhr = row['resting_hr']
        if rhr > 85: hr_s = 90.0
        elif rhr > 80: hr_s = 70.0
        elif rhr > 75: hr_s = 55.0
        elif rhr > 70: hr_s = 40.0
        elif rhr > 60: hr_s = 25.0
        else: hr_s = 15.0
    sr = row.get('sedentary_ratio', 0.7)
    if sr > 0.85: sed_s = 90.0
    elif sr > 0.75: sed_s = 70.0
    elif sr > 0.65: sed_s = 50.0
    elif sr > 0.50: sed_s = 30.0
    else: sed_s = 15.0
    sleep_s = 50.0
    if pd.notna(row.get('sleep_efficiency')):
        se = row['sleep_efficiency']
        if se < 0.70: sleep_s = 85.0
        elif se < 0.80: sleep_s = 60.0
        elif se < 0.90: sleep_s = 35.0
        else: sleep_s = 15.0
    if pd.notna(row.get('avg_mets')):
        m = row['avg_mets']
        if m > 3.0: act_s = 10.0
        elif m > 2.0: act_s = 30.0
        elif m > 1.5: act_s = 55.0
        else: act_s = 75.0
    else:
        am = row.get('active_minutes', 0)
        if am > 60: act_s = 10.0
        elif am > 30: act_s = 30.0
        elif am > 15: act_s = 55.0
        else: act_s = 75.0
    score = hr_s * 0.25 + sed_s * 0.30 + sleep_s * 0.25 + act_s * 0.20
    if score >= 65: risk = '高风险'
    elif score >= 40: risk = '中风险'
    else: risk = '低风险'
    return pd.Series({'stress_score': round(score, 2), 'risk_level': risk})


def load_and_preprocess():
    daily = pd.read_csv(DATA_DIR / 'dataset_daily.csv')
    for fmt in ['%m/%d/%Y', '%Y-%m-%d']:
        try:
            daily['activity_date'] = pd.to_datetime(daily['ActivityDate'], format=fmt)
            break
        except ValueError:
            continue

    hr = pd.read_csv(DATA_DIR / 'dataset_heartrate_minute.csv')
    hr['activity_date'] = pd.to_datetime(hr['ActivityMinute']).dt.date
    hr_daily = hr.groupby(['Id', 'activity_date']).agg(
        avg_hr=('HeartRate_Mean', 'mean'),
        resting_hr=('HeartRate_Min', 'min'),
        hrv_proxy=('HeartRate_Mean', lambda x:
                   (hr.loc[x.index, 'HeartRate_Max'] - hr.loc[x.index, 'HeartRate_Min']).mean())
    ).reset_index()

    sleep = pd.read_csv(DATA_DIR / 'dataset_sleep_minute.csv')
    sleep['activity_date'] = pd.to_datetime(sleep['ActivityMinute']).dt.date
    sleep_daily = sleep.groupby(['Id', 'activity_date']).agg(
        total_sleep_records=('SleepStage', 'count'),
        asleep_min=('SleepStage', lambda x: (x == 1).sum()),
    ).reset_index()
    sleep_daily['sleep_efficiency'] = sleep_daily['asleep_min'] / sleep_daily['total_sleep_records']

    minute = pd.read_csv(DATA_DIR / 'dataset_minute.csv')
    minute['activity_date'] = pd.to_datetime(minute['ActivityMinute']).dt.date
    mets_daily = minute.groupby(['Id', 'activity_date']).agg(
        avg_mets=('METs', lambda x: x.mean() / 10.0),
        low_mets_ratio=('METs', lambda x: (x < 15).sum() / len(x))
    ).reset_index()

    features = daily[['Id', 'activity_date', 'TotalSteps', 'VeryActiveMinutes',
                       'FairlyActiveMinutes', 'SedentaryMinutes', 'Calories',
                       'TotalMinutesAsleep', 'TotalTimeInBed']].copy()
    features.columns = ['user_id', 'activity_date', 'total_steps', 'very_active_min',
                         'fairly_active_min', 'sedentary_min', 'calories',
                         'total_sleep_min', 'total_time_in_bed']
    features['activity_date_key'] = features['activity_date'].dt.date

    features = features.merge(hr_daily.rename(columns={'Id': 'user_id'}),
                               left_on=['user_id', 'activity_date_key'],
                               right_on=['user_id', 'activity_date'],
                               how='left', suffixes=('', '_hr'))
    features = features.merge(
        sleep_daily[['Id', 'activity_date', 'sleep_efficiency']].rename(columns={'Id': 'user_id'}),
        left_on=['user_id', 'activity_date_key'],
        right_on=['user_id', 'activity_date'],
        how='left', suffixes=('', '_sleep'))
    features = features.merge(mets_daily.rename(columns={'Id': 'user_id'}),
                               left_on=['user_id', 'activity_date_key'],
                               right_on=['user_id', 'activity_date'],
                               how='left', suffixes=('', '_mets'))

    features['active_minutes'] = features['very_active_min'] + features['fairly_active_min']
    features['sedentary_ratio'] = features['sedentary_min'] / 1440.0
    features.drop(columns=[c for c in features.columns if c.endswith(('_hr', '_sleep', '_mets'))],
                  inplace=True, errors='ignore')
    if 'activity_date_key' in features.columns:
        features.drop(columns=['activity_date_key'], inplace=True)

    scores = features.apply(calc_stress, axis=1)
    features = pd.concat([features, scores], axis=1)

    features = features.sort_values(['user_id', 'activity_date'])
    features['prev_score'] = features.groupby('user_id')['stress_score'].shift(1)
    features['score_change_rate'] = (
        (features['stress_score'] - features['prev_score'])
        / features['prev_score'].replace(0, np.nan) * 100
    )
    features['score_7day_avg'] = features.groupby('user_id')['stress_score'].transform(
        lambda x: x.rolling(7, min_periods=1).mean()
    )
    return features


def main():
    features = load_and_preprocess()
    print(f"Total records: {len(features)}")
    print(f"Risk distribution:\n{features['risk_level'].value_counts()}")

    # ---- Feature columns ----
    all_cols = ['total_steps', 'sedentary_min', 'calories', 'active_minutes',
                'sedentary_ratio', 'resting_hr', 'avg_hr', 'hrv_proxy',
                'sleep_efficiency', 'avg_mets', 'low_mets_ratio', 'total_sleep_min']
    trend_cols = ['score_change_rate', 'score_7day_avg', 'prev_score',
                  'sedentary_ratio', 'active_minutes']
    available_all = [c for c in all_cols if c in features.columns]
    available_trend = [c for c in trend_cols if c in features.columns]

    corr_with_stress = features[available_all + ['stress_score']].corr()['stress_score'] \
        .drop('stress_score').abs()
    top5 = corr_with_stress.nlargest(5).index.tolist()
    print(f"Top-5 correlated features: {top5}")

    # ---- Fill missing values with column median ----
    df = features.copy()
    for col in available_all + available_trend:
        if col in df.columns:
            df[col] = df[col].fillna(df[col].median())

    le = LabelEncoder()
    y = le.fit_transform(df['risk_level'])
    X_all = df[available_all].values
    X_trend = df[available_trend].values
    X_corr = df[top5].values

    scaler_all = StandardScaler()
    scaler_trend = StandardScaler()
    scaler_corr = StandardScaler()
    X_all_s = scaler_all.fit_transform(X_all)
    X_trend_s = scaler_trend.fit_transform(X_trend)
    X_corr_s = scaler_corr.fit_transform(X_corr)

    user_ids = df['user_id'].values
    dates = df['activity_date'].values
    actual_risks = df['risk_level'].values
    n = len(df)
    results = []

    # ===== Model 1: WeightedScoring (rule-based, deterministic) =====
    print("\nModel 1: WeightedScoring...")
    for i in range(n):
        pred = calc_stress(df.iloc[i])['risk_level']
        results.append(('WeightedScoring', int(user_ids[i]), str(dates[i])[:10],
                         actual_risks[i], pred, 1 if pred == actual_risks[i] else 0,
                         None, None, None))

    # ===== Model 2: TrendAnalysis (DecisionTree + cross_val_predict) =====
    print("Model 2: TrendAnalysis (5-fold CV)...")
    dt = DecisionTreeClassifier(max_depth=8, random_state=42)
    dt_pred = cross_val_predict(dt, X_trend_s, y, cv=5)
    dt_full = DecisionTreeClassifier(max_depth=8, random_state=42).fit(X_trend_s, y)
    dt_proba = dt_full.predict_proba(X_trend_s)
    for i in range(n):
        pred_label = le.inverse_transform([dt_pred[i]])[0]
        proba = {le.inverse_transform([j])[0]: float(dt_proba[i][j])
                 for j in range(len(le.classes_))}
        results.append(('TrendAnalysis', int(user_ids[i]), str(dates[i])[:10],
                         actual_risks[i], pred_label,
                         1 if pred_label == actual_risks[i] else 0,
                         round(proba.get('高风险', 0), 4),
                         round(proba.get('中风险', 0), 4),
                         round(proba.get('低风险', 0), 4)))

    # ===== Model 3: CorrelationAnalysis (LogisticRegression + cross_val_predict) =====
    print("Model 3: CorrelationAnalysis (5-fold CV)...")
    lr = LogisticRegression(max_iter=1000, random_state=42)
    lr_pred = cross_val_predict(lr, X_corr_s, y, cv=5)
    lr_full = LogisticRegression(max_iter=1000, random_state=42).fit(X_corr_s, y)
    lr_proba = lr_full.predict_proba(X_corr_s)
    for i in range(n):
        pred_label = le.inverse_transform([lr_pred[i]])[0]
        proba = {le.inverse_transform([j])[0]: float(lr_proba[i][j])
                 for j in range(len(le.classes_))}
        results.append(('CorrelationAnalysis', int(user_ids[i]), str(dates[i])[:10],
                         actual_risks[i], pred_label,
                         1 if pred_label == actual_risks[i] else 0,
                         round(proba.get('高风险', 0), 4),
                         round(proba.get('中风险', 0), 4),
                         round(proba.get('低风险', 0), 4)))

    # ===== Model 4: KMeansClustering =====
    print("Model 4: KMeansClustering...")
    km = KMeans(n_clusters=3, random_state=42, n_init=10)
    km_labels = km.fit_predict(X_all_s)
    cluster_risk_map = {}
    for c in range(3):
        mask = km_labels == c
        cluster_risk_map[c] = pd.Series(y[mask]).mode()[0]
    for i in range(n):
        pred_encoded = cluster_risk_map[km_labels[i]]
        pred_label = le.inverse_transform([pred_encoded])[0]
        results.append(('KMeansClustering', int(user_ids[i]), str(dates[i])[:10],
                         actual_risks[i], pred_label,
                         1 if pred_label == actual_risks[i] else 0,
                         None, None, None))

    # ===== Write to MySQL =====
    print(f"\nWriting {len(results)} rows to t_classification_result...")
    conn = pymysql.connect(**MYSQL_CONFIG)
    cursor = conn.cursor()
    cursor.execute("TRUNCATE TABLE t_classification_result")
    sql = ("INSERT INTO t_classification_result "
           "(model_name, user_id, activity_date, actual_risk, predicted_risk, "
           "prediction_correct, probability_high, probability_medium, probability_low) "
           "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)")
    cursor.executemany(sql, results)
    conn.commit()

    cursor.execute(
        "SELECT model_name, COUNT(*) as cnt, SUM(prediction_correct) as correct "
        "FROM t_classification_result GROUP BY model_name"
    )
    print("\nResults:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]} records, {row[2]} correct ({row[2]/row[1]*100:.1f}%)")

    cursor.execute(
        "SELECT actual_risk, COUNT(*) FROM t_classification_result "
        "WHERE model_name='WeightedScoring' GROUP BY actual_risk"
    )
    print("\nRisk distribution:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}")

    cursor.close()
    conn.close()
    print("Done!")


if __name__ == '__main__':
    main()
