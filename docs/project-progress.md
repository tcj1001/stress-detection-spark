# 基于Spark的压力检测数据分析系统 — 项目进度日志

> 本文保留完整开发记录。项目当前目录与启动命令已于 2026-09-04 更新；日常使用请优先参考[根目录说明](../README.md)。

## 项目信息
- **题目**：基于Spark的压力检测数据分析系统的设计与实现
- **数据集**：Fitbit Bellabeat 可穿戴设备数据集（约30名用户，约31天，187万条原始记录）
- **开发语言**：Python（PySpark）、Java（Spring Boot）
- **技术栈**：Hadoop 2.7.4 + Spark 3.2.4 + MySQL 8.x + Django REST Framework + Spring Boot + Vue 3 + Element Plus + ECharts + jQuery

---

## 环境信息

### 虚拟机（CentOS 7 / VMware）— 大数据处理层
| 组件 | 版本 | 状态 |
|------|------|------|
| 操作系统 | CentOS 7 | ✅ |
| Java | OpenJDK 1.8.0_262 | ✅ |
| Hadoop | 2.7.4 | ✅ 正常运行 |
| Spark | 3.2.4（pre-built for Hadoop 2.7） | ✅ 验证通过 |
| Python | 3.8（Miniconda3-py38_4.12.0） | ✅ |
| Python依赖 | pymysql、numpy、pandas、pyspark、matplotlib | ✅ |

### Windows 11 — 应用开发层
| 组件 | 版本 | 状态 |
|------|------|------|
| MySQL | 8.x | ✅ 已配置远程访问 |
| Navicat | 已安装 | ✅ 可查看stress_db数据 |
| Python | 3.11.6 | ✅ |
| Django | 5.2.14 | ✅ 已启动，端口8000 |
| djangorestframework | 已安装 | ✅ |
| django-cors-headers | 已安装 | ✅ |
| JDK | 11.0.27 | ✅ |
| Maven | 3.8.1 | ✅ |
| Spring Boot | 2.7.18 | ✅ 已启动，端口8080 |
| Node.js | 22.16.0 | ✅ |
| Vue 3 | 3.x | ✅ 已创建前端项目，端口5173 |
| Element Plus | 最新版 | ✅ （ElementUI Vue3版） |
| ECharts | 5.x | ✅ |
| jQuery | 3.x | ✅ |

### 关键路径（虚拟机）
```
Hadoop:    /opt/stress/servers/hadoop-2.7.4/
Spark:     /opt/stress/servers/spark-3.2.4/
Miniconda: /opt/stress/miniconda3/
数据(本地): /opt/stress/data/
数据(HDFS): /stress/input/
项目脚本:  /opt/stress/project/src/analytics/
图表输出:  /opt/stress/project/output/
```

### 关键路径（Windows）
```
Django项目:       src\django\
Spring Boot项目:  src\springboot\
Vue前端项目:      src\frontend\
玻璃主题CSS:      src\frontend\src\assets\glass.css
ECharts工具:      src\frontend\src\utils\chart.js
一键启动脚本:     scripts\start.ps1
数据库更新脚本:   scripts\update_database.ps1
```

### MySQL连接信息
```
PySpark写入目标（Windows MySQL）:
  host:     通过 STRESS_DB_HOST 配置宿主机私有地址
  port:     3306
  user:     通过 STRESS_DB_USER 配置最小权限账号
  password: 通过 STRESS_DB_PASSWORD 提供，不写入仓库
  database: stress_db

Django / Spring Boot / Navicat 连接：
  host:     localhost（Windows本机）或 127.0.0.1
  port:     3306
  user:     通过 STRESS_DB_USER 配置
  password: 通过 STRESS_DB_PASSWORD 提供，不写入仓库
  database: stress_db
```

---

## 数据集说明
| 文件 | 大小 | 行数 | 内容 | 用途 |
|------|------|------|------|------|
| dataset_daily.csv | 126KB | 943行 | 每日活动汇总（步数、卡路里、睡眠、BMI） | 主特征表基础 |
| dataset_heartrate_minute.csv | 16MB | 333,420行 | 每分钟心率（均值/最小/最大） | 聚合到日粒度，计算静息心率和HRV |
| dataset_sleep_minute.csv | 8.3MB | 188,521行 | 每分钟睡眠阶段（1=睡着/2=翻动/3=清醒） | 聚合到日粒度，计算睡眠效率 |
| dataset_minute.csv | 71MB | 1,325,580行 | 每分钟活动（卡路里、强度、METs、步数） | 聚合到日粒度，METs精化活动压力分 |
| dataset_hourly.csv | 1MB | 22,099行 | 每小时活动（卡路里、强度、步数） | 单独用于24小时时段规律分析 |

---

## 分析模型说明
| 模型 | 算法 | 输入 | MySQL输出表 | 数据量 |
|------|------|------|-------------|--------|
| 模型1：综合压力评估 | 加权评分（心率25%+久坐30%+睡眠25%+METs活动20%） | 全部5个文件聚合特征 | t_daily_stress | 943条 |
| 模型2：趋势分析 | 时间序列、7日滑动平均、Lag变化率 | 模型1输出 | t_trend_analysis | 943条 |
| 模型3：相关性分析 | Pearson相关系数矩阵（7个维度） | 全部日粒度特征 | t_correlation_matrix | 49条（7×7） |
| 模型4：K-Means聚类 | K=3，StandardScaler标准化 | 用户均值特征（12个用户） | t_user_profile | 12条 |
| 模型5：时段规律分析 | 按用户+小时聚合统计 | dataset_hourly.csv | t_hourly_pattern | 792条（33用户×24小时） |
| 四模型预测对比 | 5折交叉验证+全量预测 | 943条记录×4模型 | t_classification_result | 3772条 |

### 四模型性能对比框架

将上述4个核心分析模型统一作为风险等级分类器进行对比评估：

| 对比模型 | 分类方法 | 特征选择 | 准确率（5折CV） |
|----------|----------|----------|--------|
| 综合压力评估 | 规则阈值（≥65高/40-65中/<40低） | stress_score阈值划分 | 69.9% |
| 趋势分析 | DecisionTreeClassifier | score_change_rate, score_7day_avg, prev_score, sedentary_ratio, active_minutes | 89.1% |
| 相关性分析 | LogisticRegression | 与stress_score相关性Top5特征 | 86.1% |
| K-Means聚类 | KMeans(k=3)标签映射 | 全部12维生理行为特征 | 54.9% |

```
评估指标：准确率、精确率、召回率、F1分数（整体+各风险等级）
收敛性分析：学习曲线（训练集从20%递增至100%）
特征重要性：各模型关键特征排名
分类预测：全部943条记录的逐条预测结果（5折交叉验证）
输出表：t_model_metrics, t_learning_curve, t_feature_importance, t_classification_result
```

### 压力评分维度权重
```
心率压力分   （resting_hr）    × 25%   → 静息心率越高压力越大
久坐压力分   （sedentary_ratio）× 30%  → 久坐比例越高压力越大
睡眠压力分   （sleep_efficiency）× 25% → 睡眠效率越低压力越大
活动压力分   （avg_mets）       × 20%  → METs值越低压力越大（有METs数据时优先使用）

风险等级：≥65分 → 高风险 | 40~65分 → 中风险 | <40分 → 低风险
```

### K-Means聚类结果标签
```
高压久坐型  → 平均压力分最高、久坐比例最大
睡眠不足型  → 睡眠效率低、压力中等
健康活跃型  → 平均压力分最低、METs活跃度高
```

---

## MySQL表结构（10张表）

```sql
-- 每日压力评分表（模型1+2输出）
CREATE TABLE t_daily_stress (
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
    score_7day_avg DECIMAL(5,2)
);

-- 趋势分析表（模型2输出）
CREATE TABLE t_trend_analysis (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT,
    activity_date DATE,
    stress_score DECIMAL(5,2),
    score_7day_avg DECIMAL(5,2),
    score_change_rate DECIMAL(8,4),
    trend_label VARCHAR(20)
);

-- 相关性矩阵表（模型3输出）
CREATE TABLE t_correlation_matrix (
    id INT AUTO_INCREMENT PRIMARY KEY,
    feature_x VARCHAR(50),
    feature_y VARCHAR(50),
    corr_value DECIMAL(6,4)
);

-- 用户画像表（模型4聚类输出）
CREATE TABLE t_user_profile (
    user_id BIGINT PRIMARY KEY,
    cluster_id INT,
    cluster_label VARCHAR(20),
    avg_stress_score DECIMAL(5,2),
    avg_sleep_efficiency DECIMAL(5,4),
    avg_active_minutes DECIMAL(6,2),
    avg_resting_hr DECIMAL(5,2),
    avg_sedentary_ratio DECIMAL(5,4),
    risk_level VARCHAR(10)
);

-- 时段规律表（模型5输出）
CREATE TABLE t_hourly_pattern (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT,
    hour_of_day INT,
    avg_intensity DECIMAL(6,4),
    avg_calories DECIMAL(8,4),
    avg_steps DECIMAL(8,2),
    record_count INT
);

-- 系统用户表（Spring Boot自动建表）
CREATE TABLE sys_user (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    email VARCHAR(100),
    role VARCHAR(20) DEFAULT 'USER',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 分类预测结果表（四模型对比输出）
CREATE TABLE t_classification_result (
    id INT AUTO_INCREMENT PRIMARY KEY,
    model_name VARCHAR(50),
    user_id BIGINT,
    activity_date DATE,
    actual_risk VARCHAR(10),
    predicted_risk VARCHAR(10),
    prediction_correct TINYINT,
    probability_high DECIMAL(6,4),
    probability_medium DECIMAL(6,4),
    probability_low DECIMAL(6,4)
);

-- 特征重要性表（四模型对比输出）
CREATE TABLE t_feature_importance (
    id INT AUTO_INCREMENT PRIMARY KEY,
    model_name VARCHAR(50),
    feature_name VARCHAR(50),
    importance DECIMAL(10,6),
    rank_order INT
);

-- 模型评估指标表（四模型对比输出）
CREATE TABLE t_model_metrics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    model_name VARCHAR(50),
    metric_name VARCHAR(50),
    metric_value DECIMAL(10,6)
);

-- 学习曲线表（四模型收敛性分析）
CREATE TABLE t_learning_curve (
    id INT AUTO_INCREMENT PRIMARY KEY,
    model_name VARCHAR(50),
    train_size INT,
    train_score DECIMAL(10,6),
    test_score DECIMAL(10,6)
);
```

---

## 后端架构（双后端）

### Django REST Framework（端口 8000）— 数据分析API层
| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/stress/users/` | GET | 所有用户ID列表 |
| `/api/stress/chart/?user_id=xxx` | GET | 折线图数据（日期+压力分+7日均线） |
| `/api/stress/risk-summary/` | GET | 风险等级饼图数据 |
| `/api/stress/?user_id=xxx` | GET | 每日压力列表（支持分页、日期筛选） |
| `/api/stress/prediction/?user_id=xxx` | GET | 四模型预测结果对比（实际vs预测） |
| `/api/stress/prediction-users/` | GET | 有预测数据的用户ID列表 |
| `/api/trend/chart/?user_id=xxx` | GET | 趋势变化图（变化率+趋势标签） |
| `/api/trend/forecast/?user_id=xxx` | GET | 未来7天趋势预测（线性回归+EWMA+置信区间） |
| `/api/correlation/heatmap/` | GET | 7×7相关性热力图数据 |
| `/api/profile/cluster-summary/` | GET | 聚类雷达图数据 |
| `/api/profile/` | GET | 全部用户画像 |
| `/api/hourly/users/` | GET | 时段规律用户ID列表 |
| `/api/hourly/chart/?user_id=xxx` | GET | 24小时柱状图数据（按用户） |
| `/api/model/metrics/` | GET | 四模型评估指标（准确率/精确率/召回率/F1） |
| `/api/model/learning-curve/` | GET | 四模型学习曲线数据（收敛性分析） |
| `/api/model/feature-importance/` | GET | 四模型特征重要性排名 |
| `/api/model/confusion-matrix/` | GET | 四模型混淆矩阵+预测分布 |

### Spring Boot（端口 8080）— 用户管理层
| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/auth/register` | POST | 用户注册 |
| `/api/auth/login` | POST | 登录（返回JWT token） |
| `/api/admin/users` | GET | 用户列表（需ADMIN角色） |
| `/api/admin/users/{id}` | DELETE | 删除用户（需ADMIN角色） |

---

## 核心脚本说明

### stress_analysis.py
虚拟机示例路径：`/opt/stress/project/src/analytics/stress_analysis.py`
Windows源码：`src/analytics/stress_analysis.py`

| 函数 | 作用 |
|------|------|
| `load_and_preprocess()` | 加载全部5个CSV，聚合到日粒度后Join，生成943条主特征表 |
| `model1_stress_score()` | 加权计算综合压力评分（0-100），划分高/中/低风险等级 |
| `model2_trend()` | 时间序列趋势分析：Lag变化率 + 7日滑动平均 + 趋势标签 |
| `model3_correlation()` | Pearson相关系数矩阵（7维），输出49条长表格式 |
| `model4_kmeans()` | K-Means(k=3)用户聚类，StandardScaler标准化，自动打标签 |
| `model5_hourly_pattern()` | dataset_hourly.csv按用户+小时聚合，输出每用户24小时规律 |
| `model_comparison()` | 四模型性能对比：将4个分析模型统一作为分类器评估，生成学习曲线+指标+特征重要性 |
| `generate_training_charts()` | 自动生成3张300DPI高清训练曲线对比图（四模型损失/准确率对比、各模型训练vs验证） |
| `write_to_mysql()` | Spark DataFrame → Windows MySQL（自动TRUNCATE后写入） |
| `append_to_mysql()` | Spark DataFrame → Windows MySQL（追加写入，不清空） |

### run_ml_models.py（Windows本地版四模型对比脚本）
路径：`src/analytics/run_ml_models.py`

| 功能 | 说明 |
|------|------|
| 读取本地CSV | 默认读取 `data/raw` 中的5个CSV文件，无需HDFS；可用 `STRESS_DATA_DIR` 覆盖 |
| scikit-learn实现 | DecisionTreeClassifier + LogisticRegression + KMeans |
| 学习曲线 | sklearn.model_selection.learning_curve 生成收敛性数据 |
| 四模型对比 | 综合评估、趋势分析、相关性分析、K-Means聚类的分类性能 |
| 写入MySQL | 结果写入t_model_metrics、t_learning_curve、t_feature_importance |

### gen_classification.py（四模型分类预测数据生成脚本）
路径：`src/analytics/gen_classification.py`

| 功能 | 说明 |
|------|------|
| 全量预测 | 943条记录×4个模型=3772条逐条预测结果 |
| 中位数填充 | 缺失特征用列中位数填充，确保全部记录参与 |
| 交叉验证 | DecisionTree和LogisticRegression使用5折交叉验证 |
| 三风险等级 | 高风险(182)、中风险(457)、低风险(304) |
| 写入MySQL | 结果写入t_classification_result |

---

## 项目进度

### ✅ 已完成（大数据处理层）
- [x] **2026-05-08** 虚拟机环境搭建：Hadoop 2.7.4、Spark 3.2.4、Python 3.8(Miniconda)
- [x] **2026-05-08** 安装Python依赖：pymysql、numpy、pandas
- [x] **2026-05-08** Spark验证：`pi.py` 本地模式运行成功
- [x] **2026-05-08** 5个CSV文件上传至HDFS `/stress/input/`
- [x] **2026-05-08** Windows MySQL配置：创建stress_db、5张表、开放远程连接、防火墙放行3306
- [x] **2026-05-08** PySpark主分析脚本 stress_analysis.py 开发完成（5个模型）
- [x] **2026-05-08** 全部5个模型运行成功，数据写入Windows MySQL（Navicat可查看）
  - t_daily_stress：943条
  - t_trend_analysis：943条
  - t_correlation_matrix：49条
  - t_user_profile：12条
  - t_hourly_pattern：792条（33用户×24小时）

### ✅ 已完成（应用层后端）
- [x] **2026-05-10** Django REST Framework 项目搭建，连接MySQL，10个API接口全部验证通过
- [x] **2026-05-10** Spring Boot 项目搭建，JWT鉴权，用户注册/登录/管理接口完成
- [x] **2026-05-10** 两个后端均配置CORS，支持Vue前端跨域调用

### ✅ 已完成（前端层）
- [x] **2026-05-10** 创建 Vue 3 项目 stress_vue，安装 Element Plus、ECharts、jQuery、axios
- [x] **2026-05-10** 完成登录/注册页面（对接 Spring Boot JWT 鉴权）
- [x] **2026-05-10** 完成6个数据可视化页面：总览仪表盘、每日压力、趋势分析、相关性热力图、用户画像、时段规律
- [x] **2026-05-10** 完成模型性能对比页面：四模型指标对比、学习曲线、各等级F1/召回率、特征重要性（高清图+不同线型）
- [x] **2026-05-10** 配置路由守卫，未登录自动跳转登录页
- [x] **2026-05-12** 每日压力页增加四模型风险预测对比：准确率卡片+预测时间线+正误分布饼图+逐日明细表格
- [x] **2026-05-12** 趋势分析页增加未来趋势预测：摘要卡片（方向/斜率）+历史与预测合并折线图（置信区间）+逐日预测明细表
- [x] **2026-05-12** 相关性分析页增加关键发现：压力关联强度柱状图+最显著特征对图+自动生成文字摘要（核心发现/正负相关/联动效应/健康启示）
- [x] **2026-05-12** 模型对比页增加混淆矩阵热力图（4个并排）+预测分布对比图+预测正误统计图

### ✅ 已完成（UI / 体验优化）
- [x] **2026-05-13** 相关性分析页新增上三角相关系数矩阵图
- [x] **2026-05-13** 模型对比页特征重要性改为四模型独立柱状图（2×2布局），解决不同特征集交叉显示0值问题
- [x] **2026-05-13** 补全综合压力评估（权重）和K-Means聚类（聚类中心方差）的特征重要性数据
- [x] **2026-05-13** 前端日期统一显示为2026年（API响应拦截器自动替换）
- [x] **2026-05-13** 全站改造为玻璃拟态（Glassmorphism）风格：深蓝渐变背景+毛玻璃卡片+ECharts暗色主题+半透明侧边栏
- [x] **2026-05-13** 统一风险等级Tag样式：高风险（红色半透明底+浅红字）、中风险（橙色半透明底+金黄字）、低风险（绿色半透明底+浅绿字）
- [x] **2026-05-13** 适配玻璃主题下的下拉选择器、表格、表单标签、滚动条等组件样式

### ✅ 已完成（机器学习模型）
- [x] **2026-05-11** 四模型性能对比框架：综合压力评估(69.9%) + 趋势分析(89.1%) + 相关性分析(86.1%) + K-Means聚类(54.9%)
- [x] **2026-05-11** 新增MySQL表 t_learning_curve，更新 t_model_metrics、t_feature_importance
- [x] **2026-05-11** Windows本地对比脚本 run_ml_models.py 运行成功，写入56条指标+32条学习曲线+10条特征重要性
- [x] **2026-05-11** 更新PySpark脚本 stress_analysis.py，新增 model_comparison() 函数（Spark MLlib实现）
- [x] **2026-05-11** Django新增3个API接口（模型指标/学习曲线/特征重要性）
- [x] **2026-05-11** Vue新增模型性能对比页面：指标卡片+柱状图+学习曲线+各等级F1/召回率+特征重要性（高清+不同线型）
- [x] **2026-05-12** gen_classification.py 增强版：全部943条记录×4模型=3772条预测结果，5折交叉验证，三风险等级全覆盖
- [x] **2026-05-12** t_hourly_pattern 数据修复：从CSV重新按用户×小时聚合，792条记录（33用户×24小时）
- [x] **2026-05-13** stress_analysis.py 新增 generate_training_charts()，Spark处理数据时自动生成3张300DPI高清训练曲线图
- [x] **2026-05-13** stress_analysis.py 全部进度提示语改为中文输出
- [x] **2026-05-13** 虚拟机新增Python依赖 matplotlib，图表输出至项目 `output/` 目录

### ✅ 已完成（系统联调）
- [x] **2026-05-12** 三端服务存活验证：Spring Boot(8080) + Django(8000) + Vue(5173) 全部正常运行
- [x] **2026-05-12** Spring Boot 接口测试：注册/登录/JWT鉴权/角色权限控制(403) 全部通过
- [x] **2026-05-12** Django 全部17个API端点测试通过，数据格式和内容正确
- [x] **2026-05-12** Vue 9个页面路由全部200，组件编译无错误
- [x] **2026-05-12** 端到端流程验证：注册→登录→Token→仪表盘→每日压力(含预测)→趋势(含预测)→相关性→模型对比 全链路通过
- [x] **2026-05-12** MySQL 10张表数据完整性检查：共6809条记录，关键字段无NULL异常

### ⏳ 待完成
- [ ] 论文撰写

---

## 启动命令速查

```bash
# 【虚拟机】启动Hadoop
start-dfs.sh && start-yarn.sh

# 【虚拟机】运行主分析脚本（约5-8分钟）
spark-submit --master local[*] /opt/stress/project/src/analytics/stress_analysis.py

# 【虚拟机】查看HDFS数据文件
hdfs dfs -ls /stress/input/

# 【虚拟机】运行前通过环境变量提供数据库地址、用户和密码
export STRESS_DB_HOST='<windows-host-private-ip>'
export STRESS_DB_USER='<least-privilege-db-user>'
export STRESS_DB_PASSWORD='<database-password>'
```

```powershell
# 【Windows】更新/初始化数据库（保留现有分析数据）
.\scripts\update_database.ps1

# 【Windows】一键启动 Django、Spring Boot、Vue
.\scripts\start.ps1

# 【Windows】停止由一键脚本启动的三个服务
.\scripts\stop.ps1
```

以上命令均从项目根目录执行。启动成功后访问：`http://127.0.0.1:5173`，日志保存在 `logs/`。

如需分别启动三个服务：

```powershell
# Django（端口8000）
py -3.11 .\scripts\run_django.py

# Spring Boot（端口8080）
mvn -s .\config\maven-settings.xml -f .\src\springboot\pom.xml spring-boot:run

# Vue（端口5173）
npm --prefix .\src\frontend run dev -- --host 127.0.0.1
```

数据库地址、账号和密码必须通过 `config/local.env.ps1` 或进程环境变量提供。该本机配置文件已被 Git 忽略，Django、Spring Boot 和数据脚本会共同使用这些变量。

---

## 更新记录
| 日期 | 内容 |
|------|------|
| 2026-05-08 | 完成虚拟机环境搭建（Hadoop/Spark/Python）、数据上传HDFS、Spark验证 |
| 2026-05-08 | 创建MySQL数据库 stress_db，建立5张表 |
| 2026-05-08 | 完成stress_analysis.py，5个模型全部运行成功 |
| 2026-05-08 | 整合全部5个CSV文件，新增METs特征（dataset_minute）和时段规律分析（dataset_hourly） |
| 2026-05-08 | 配置Windows MySQL远程访问，数据成功写入Windows MySQL，Navicat可见 |
| 2026-05-10 | 搭建Django REST Framework后端，完成9个数据分析API接口，连接MySQL验证通过 |
| 2026-05-10 | 搭建Spring Boot后端，完成JWT鉴权、用户注册/登录/管理接口，配置双后端CORS |
| 2026-05-10 | 创建Vue 3前端项目，集成Element Plus、ECharts、jQuery，完成登录/注册及6个可视化页面 |
| 2026-05-11 | 时段规律模块改造：PySpark/MySQL/Django/Vue全链路支持按用户分组，新增用户选择器，数据从24条扩展为792条（33用户×24小时） |
| 2026-05-11 | 四模型性能对比框架：综合压力评估+趋势分析+相关性分析+K-Means聚类，统一作为风险分类器进行对比评估 |
| 2026-05-11 | 新增t_learning_curve表、更新t_model_metrics，Windows本地run_ml_models.py运行成功 |
| 2026-05-11 | 更新PySpark脚本新增model_comparison()函数（Spark MLlib），Django新增3个模型对比API |
| 2026-05-11 | Vue新增模型性能对比页面：指标卡片+柱状图+学习曲线+各等级F1/召回率+特征重要性（高清+不同线型） |
| 2026-05-12 | 修复t_hourly_pattern数据（user_id为NULL→重新从CSV按用户×小时聚合，792条记录） |
| 2026-05-12 | 每日压力页增加四模型风险预测对比（准确率卡片+预测时间线+正误饼图+逐日明细表格） |
| 2026-05-12 | 趋势分析页增加未来7天趋势预测（线性回归+EWMA混合预测+置信区间+风险等级标注） |
| 2026-05-12 | 相关性分析页增加关键发现摘要（关联强度图+显著特征对图+自动生成6类文字洞察） |
| 2026-05-12 | 模型对比页增加混淆矩阵热力图（4个并排）+预测分布对比图+预测正误统计图 |
| 2026-05-12 | gen_classification.py增强版：943条全量记录、5折交叉验证、三风险等级，写入3772条预测结果 |
| 2026-05-12 | Django新增4个API接口（预测结果/预测用户列表/趋势预测/混淆矩阵），总计17个数据分析接口 |
| 2026-05-12 | 三端联调测试通过：Spring Boot(4接口) + Django(17接口) + Vue(9页面) + MySQL(10表/6809条) 全链路验证 |
| 2026-05-13 | stress_analysis.py新增自动生成训练曲线图功能（3张300DPI高清图：四模型对比+各模型准确率+各模型损失） |
| 2026-05-13 | stress_analysis.py全部进度提示语改为中文，虚拟机新增matplotlib依赖 |
| 2026-05-13 | 相关性分析页新增上三角相关系数矩阵图 |
| 2026-05-13 | 模型对比页特征重要性改为四模型独立柱状图，补全WeightedScoring和KMeansClustering特征重要性数据 |
| 2026-05-13 | 前端日期统一显示为2026年（Django API响应拦截器自动替换2016→2026） |
| 2026-05-13 | 全站UI改造为玻璃拟态风格：深蓝渐变背景、毛玻璃卡片、ECharts glass暗色主题、半透明侧边栏 |
| 2026-05-13 | 适配玻璃主题：下拉选择器、风险等级Tag（红/橙/绿半透明）、表格、表单标签、滚动条等组件 |
