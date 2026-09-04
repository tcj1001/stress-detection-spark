"""
4模型性能对比分析脚本（Windows本地版）
读取CSV数据 → 4个模型分别预测风险等级 → 性能对比数据写入MySQL

模型1: 综合压力评估（加权评分法）
模型2: 趋势分析（趋势特征 + 决策树）
模型3: 相关性分析（Pearson特征选择 + 逻辑回归）
模型4: K-Means聚类（聚类标签映射风险等级）
"""

import pandas as pd
import numpy as np
import pymysql
from project_config import DATA_DIR, MYSQL_CONFIG
from sklearn.tree import DecisionTreeClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.cluster import KMeans
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import train_test_split, learning_curve
from sklearn.metrics import (accuracy_score, precision_score, recall_score,
                             f1_score, confusion_matrix)

def write_to_mysql(df, table_name, truncate=True):
    conn = pymysql.connect(**MYSQL_CONFIG)
    cursor = conn.cursor()
    if truncate:
        cursor.execute(f"TRUNCATE TABLE {table_name}")

    cols = list(df.columns)
    placeholders = ','.join(['%s'] * len(cols))
    col_names = ','.join(cols)
    sql = f"INSERT INTO {table_name} ({col_names}) VALUES ({placeholders})"

    data = []
    for row in df.itertuples(index=False):
        converted = []
        for v in row:
            if hasattr(v, 'item'):
                converted.append(v.item())
            elif pd.isna(v):
                converted.append(None)
            else:
                converted.append(v)
        data.append(tuple(converted))

    cursor.executemany(sql, data)
    conn.commit()
    cursor.close()
    conn.close()
    print(f"  [OK] {len(data)} rows -> {table_name}")


def load_and_preprocess():
    print("=" * 55)
    print("Step 1: Data Loading & Feature Engineering")
    print("=" * 55)

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
    features.drop(columns=[c for c in features.columns
                           if c.endswith(('_hr', '_sleep', '_mets'))],
                  inplace=True, errors='ignore')
    if 'activity_date_key' in features.columns:
        features.drop(columns=['activity_date_key'], inplace=True)

    # --- Weighted scoring (ground truth labels) ---
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
        return pd.Series({'stress_score': round(score, 2), 'risk_level': risk,
                          'hr_score': hr_s, 'sleep_score': sleep_s,
                          'active_score': act_s, 'sedentary_score': sed_s})

    scores = features.apply(calc_stress, axis=1)
    features = pd.concat([features, scores], axis=1)

    # --- Trend features ---
    features = features.sort_values(['user_id', 'activity_date'])
    features['prev_score'] = features.groupby('user_id')['stress_score'].shift(1)
    features['score_change_rate'] = ((features['stress_score'] - features['prev_score'])
                                     / features['prev_score'].replace(0, np.nan) * 100)
    features['score_7day_avg'] = (features.groupby('user_id')['stress_score']
                                   .transform(lambda x: x.rolling(7, min_periods=1).mean()))

    print(f"  Done: {len(features)} records")
    print(f"  Risk distribution: {features['risk_level'].value_counts().to_dict()}")
    return features


def evaluate_model(y_true, y_pred, model_name, le):
    acc = accuracy_score(y_true, y_pred)
    prec = precision_score(y_true, y_pred, average='weighted', zero_division=0)
    rec = recall_score(y_true, y_pred, average='weighted', zero_division=0)
    f1 = f1_score(y_true, y_pred, average='weighted', zero_division=0)

    # Per-class metrics
    labels = le.classes_
    prec_per = precision_score(y_true, y_pred, average=None, zero_division=0, labels=range(len(labels)))
    rec_per = recall_score(y_true, y_pred, average=None, zero_division=0, labels=range(len(labels)))
    f1_per = f1_score(y_true, y_pred, average=None, zero_division=0, labels=range(len(labels)))

    print(f"  {model_name}: Acc={acc:.4f} Prec={prec:.4f} Rec={rec:.4f} F1={f1:.4f}")

    metrics = [
        (model_name, 'accuracy', acc),
        (model_name, 'precision', prec),
        (model_name, 'recall', rec),
        (model_name, 'f1', f1),
    ]
    for i, label in enumerate(labels):
        metrics.append((model_name, f'precision_{label}', prec_per[i]))
        metrics.append((model_name, f'recall_{label}', rec_per[i]))
        metrics.append((model_name, f'f1_{label}', f1_per[i]))

    cm = confusion_matrix(y_true, y_pred)
    for i, actual in enumerate(labels):
        for j, pred in enumerate(labels):
            metrics.append((model_name, f'cm_{actual}_{pred}', int(cm[i][j])))

    return pd.DataFrame(metrics, columns=['model_name', 'metric_name', 'metric_value'])


def compute_learning_curves(estimator, X, y, model_name, cv=5):
    train_sizes = np.linspace(0.2, 1.0, 8)
    train_sizes_abs, train_scores, test_scores = learning_curve(
        estimator, X, y, train_sizes=train_sizes, cv=cv,
        scoring='accuracy', n_jobs=-1, random_state=42)

    rows = []
    for i in range(len(train_sizes_abs)):
        rows.append({
            'model_name': model_name,
            'train_size': int(train_sizes_abs[i]),
            'train_score': round(float(train_scores[i].mean()), 6),
            'test_score': round(float(test_scores[i].mean()), 6),
        })
    return pd.DataFrame(rows)


def run_comparison(features):
    # ========== Prepare common data ==========
    all_feature_cols = ['total_steps', 'sedentary_min', 'calories', 'active_minutes',
                        'sedentary_ratio', 'resting_hr', 'avg_hr', 'hrv_proxy',
                        'sleep_efficiency', 'avg_mets', 'low_mets_ratio', 'total_sleep_min']
    available_cols = [c for c in all_feature_cols if c in features.columns]

    trend_cols = ['score_change_rate', 'score_7day_avg', 'prev_score']
    trend_available = [c for c in trend_cols if c in features.columns]

    df = features.dropna(subset=available_cols + trend_available + ['risk_level']).copy()
    print(f"\n  Common evaluation set: {len(df)} samples")

    le = LabelEncoder()
    y = le.fit_transform(df['risk_level'])
    X_all = df[available_cols].values
    X_trend = df[trend_available + ['sedentary_ratio', 'active_minutes']].values

    # Correlation-based feature selection: top 5 correlated with stress_score
    corr_with_stress = df[available_cols + ['stress_score']].corr()['stress_score'].drop('stress_score').abs()
    top5_features = corr_with_stress.nlargest(5).index.tolist()
    X_corr = df[top5_features].values
    print(f"  Top-5 correlated features: {top5_features}")

    scaler_all = StandardScaler()
    X_all_scaled = scaler_all.fit_transform(X_all)
    scaler_trend = StandardScaler()
    X_trend_scaled = scaler_trend.fit_transform(X_trend)
    scaler_corr = StandardScaler()
    X_corr_scaled = scaler_corr.fit_transform(X_corr)

    X_train_all, X_test_all, y_train, y_test = train_test_split(
        X_all_scaled, y, test_size=0.2, random_state=42, stratify=y)
    X_train_trend, X_test_trend, _, _ = train_test_split(
        X_trend_scaled, y, test_size=0.2, random_state=42, stratify=y)
    X_train_corr, X_test_corr, _, _ = train_test_split(
        X_corr_scaled, y, test_size=0.2, random_state=42, stratify=y)

    all_metrics = []
    all_lc = []
    all_fi = []

    # ========== Model 1: Weighted Scoring ==========
    print("\n" + "=" * 55)
    print("Model 1: Weighted Scoring (Rule-based)")
    print("=" * 55)

    def weighted_score_predict(X_scaled, scaler, cols):
        X_orig = scaler.inverse_transform(X_scaled)
        preds = []
        for row in X_orig:
            fdict = dict(zip(cols, row))
            rhr = fdict.get('resting_hr', 70)
            if rhr > 85: hr_s = 90
            elif rhr > 80: hr_s = 70
            elif rhr > 75: hr_s = 55
            elif rhr > 70: hr_s = 40
            elif rhr > 60: hr_s = 25
            else: hr_s = 15
            sr = fdict.get('sedentary_ratio', 0.7)
            if sr > 0.85: sed_s = 90
            elif sr > 0.75: sed_s = 70
            elif sr > 0.65: sed_s = 50
            elif sr > 0.50: sed_s = 30
            else: sed_s = 15
            se = fdict.get('sleep_efficiency', 0.8)
            if se < 0.70: sl_s = 85
            elif se < 0.80: sl_s = 60
            elif se < 0.90: sl_s = 35
            else: sl_s = 15
            mets = fdict.get('avg_mets', 1.5)
            if mets > 3.0: act_s = 10
            elif mets > 2.0: act_s = 30
            elif mets > 1.5: act_s = 55
            else: act_s = 75
            score = hr_s * 0.25 + sed_s * 0.30 + sl_s * 0.25 + act_s * 0.20
            if score >= 65: preds.append('高风险')
            elif score >= 40: preds.append('中风险')
            else: preds.append('低风险')
        return le.transform(preds)

    y_pred_ws = weighted_score_predict(X_test_all, scaler_all, available_cols)
    all_metrics.append(evaluate_model(y_test, y_pred_ws, 'WeightedScoring', le))

    ws_features = ['resting_hr', 'sedentary_ratio', 'sleep_efficiency', 'avg_mets']
    ws_weights = [0.25, 0.30, 0.25, 0.20]
    fi_ws = pd.DataFrame({
        'model_name': 'WeightedScoring',
        'feature_name': ws_features,
        'importance': ws_weights,
        'rank_order': np.argsort(-np.array(ws_weights)).argsort() + 1
    })
    all_fi.append(fi_ws)

    # Learning curve for weighted scoring (evaluate on increasing test sizes)
    lc_rows = []
    for frac in np.linspace(0.2, 1.0, 8):
        n = max(int(len(X_all_scaled) * frac), 10)
        idx = np.random.RandomState(42).choice(len(X_all_scaled), n, replace=False)
        y_p = weighted_score_predict(X_all_scaled[idx], scaler_all, available_cols)
        acc = accuracy_score(y[idx], y_p)
        lc_rows.append({'model_name': 'WeightedScoring', 'train_size': n,
                        'train_score': round(acc, 6), 'test_score': round(acc, 6)})
    all_lc.append(pd.DataFrame(lc_rows))

    # ========== Model 2: Trend Analysis (Decision Tree) ==========
    print("\n" + "=" * 55)
    print("Model 2: Trend Analysis (Decision Tree)")
    print("=" * 55)
    dt = DecisionTreeClassifier(max_depth=8, random_state=42)
    dt.fit(X_train_trend, y_train)
    y_pred_dt = dt.predict(X_test_trend)
    all_metrics.append(evaluate_model(y_test, y_pred_dt, 'TrendAnalysis', le))
    all_lc.append(compute_learning_curves(
        DecisionTreeClassifier(max_depth=8, random_state=42),
        X_trend_scaled, y, 'TrendAnalysis'))

    fi_trend = pd.DataFrame({
        'model_name': 'TrendAnalysis',
        'feature_name': trend_available + ['sedentary_ratio', 'active_minutes'],
        'importance': np.round(dt.feature_importances_, 6),
        'rank_order': np.argsort(-dt.feature_importances_).argsort() + 1
    })
    all_fi.append(fi_trend)

    # ========== Model 3: Correlation Analysis (Logistic Regression) ==========
    print("\n" + "=" * 55)
    print("Model 3: Correlation Analysis (Logistic Regression)")
    print("=" * 55)
    lr = LogisticRegression(max_iter=1000, random_state=42)
    lr.fit(X_train_corr, y_train)
    y_pred_lr = lr.predict(X_test_corr)
    all_metrics.append(evaluate_model(y_test, y_pred_lr, 'CorrelationAnalysis', le))
    all_lc.append(compute_learning_curves(
        LogisticRegression(max_iter=1000, random_state=42),
        X_corr_scaled, y, 'CorrelationAnalysis'))

    coef_importance = np.mean(np.abs(lr.coef_), axis=0)
    fi_corr = pd.DataFrame({
        'model_name': 'CorrelationAnalysis',
        'feature_name': top5_features,
        'importance': np.round(coef_importance, 6),
        'rank_order': np.argsort(-coef_importance).argsort() + 1
    })
    all_fi.append(fi_corr)

    # ========== Model 4: K-Means Clustering ==========
    print("\n" + "=" * 55)
    print("Model 4: K-Means Clustering")
    print("=" * 55)
    km = KMeans(n_clusters=3, random_state=42, n_init=10)
    km_labels = km.fit_predict(X_all_scaled)

    # Map clusters to most common risk level
    cluster_risk_map = {}
    for c in range(3):
        mask = km_labels == c
        most_common = pd.Series(y[mask]).mode()[0]
        cluster_risk_map[c] = most_common

    y_pred_km_all = np.array([cluster_risk_map[c] for c in km_labels])
    y_pred_km_test = np.array([cluster_risk_map[c]
                               for c in km.predict(X_test_all)])
    all_metrics.append(evaluate_model(y_test, y_pred_km_test, 'KMeansClustering', le))

    # K-Means convergence: inertia with increasing K, and accuracy with increasing data
    lc_rows = []
    for frac in np.linspace(0.2, 1.0, 8):
        n = max(int(len(X_all_scaled) * frac), 10)
        idx = np.random.RandomState(42).choice(len(X_all_scaled), n, replace=False)
        km_tmp = KMeans(n_clusters=3, random_state=42, n_init=10)
        labels_tmp = km_tmp.fit_predict(X_all_scaled[idx])
        cmap_tmp = {}
        for c in range(3):
            mask = labels_tmp == c
            if mask.sum() > 0:
                cmap_tmp[c] = pd.Series(y[idx][mask]).mode()[0]
            else:
                cmap_tmp[c] = 0
        y_p_tmp = np.array([cmap_tmp[c] for c in labels_tmp])
        acc = accuracy_score(y[idx], y_p_tmp)
        lc_rows.append({'model_name': 'KMeansClustering', 'train_size': n,
                        'train_score': round(acc, 6), 'test_score': round(acc, 6)})
    all_lc.append(pd.DataFrame(lc_rows))

    center_var = np.var(km.cluster_centers_, axis=0)
    center_var_norm = center_var / center_var.sum()
    fi_km = pd.DataFrame({
        'model_name': 'KMeansClustering',
        'feature_name': available_cols,
        'importance': np.round(center_var_norm, 6),
        'rank_order': np.argsort(-center_var_norm).argsort() + 1
    })
    all_fi.append(fi_km)

    # ========== Write all results to MySQL ==========
    print("\n" + "=" * 55)
    print("Writing results to MySQL...")
    print("=" * 55)

    metrics_df = pd.concat(all_metrics, ignore_index=True)
    write_to_mysql(metrics_df, 't_model_metrics')

    lc_df = pd.concat(all_lc, ignore_index=True)
    write_to_mysql(lc_df, 't_learning_curve')

    if all_fi:
        fi_df = pd.concat(all_fi, ignore_index=True)
        write_to_mysql(fi_df, 't_feature_importance')


def main():
    features = load_and_preprocess()
    run_comparison(features)

    print("\n" + "=" * 55)
    print("Done! Results written to MySQL stress_db:")
    print("  - t_model_metrics       (4 models comparison)")
    print("  - t_learning_curve      (convergence curves)")
    print("  - t_feature_importance  (feature rankings)")
    print("=" * 55)


if __name__ == '__main__':
    main()
