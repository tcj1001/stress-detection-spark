# 基于 Spark 的压力检测数据分析系统

本项目使用 Fitbit 可穿戴设备数据完成压力评分、趋势分析、相关性分析、用户聚类和时段规律分析，并通过 Django REST API、Spring Boot 用户服务和 Vue 3 前端提供查询与可视化能力。

## 系统组成

| 模块 | 技术 | 默认端口 | 目录 |
|---|---|---:|---|
| 数据分析 API | Django REST Framework | 8000 | `src/django` |
| 用户与认证 API | Spring Boot | 8080 | `src/springboot` |
| Web 前端 | Vue 3 + Vite | 5173 | `src/frontend` |
| 分析与建表脚本 | pandas / scikit-learn / PySpark | - | `src/analytics` |
| 数据库 | MySQL 8.x | 3306 | `stress_db` |

## 目录结构

```text
.
|-- README.md                  # 项目入口说明
|-- assets/
|   |-- model-figures/         # 本项目生成的模型图
|   `-- reference-figures/     # 参考图
|-- config/
|   |-- environment.example.ps1 # 可公开的环境变量模板
|   |-- maven-settings.xml
|   `-- requirements-windows.txt
|-- data/
|   `-- raw/                   # 5 个原始 CSV 数据集
|-- docs/
|   |-- README.md              # 文档索引
|   |-- frontend-features.md   # 前端页面说明
|   |-- project-overview.md    # 项目介绍
|   `-- project-progress.md    # 完整开发记录
|-- logs/                      # 服务运行日志和 PID 文件
|-- packages/                  # 离线安装包说明；大文件仅保留在本机
|-- scripts/                   # Windows 启动、停止和数据库脚本
`-- src/
    |-- analytics/             # 本地分析、分类、PySpark 和建表代码
    |-- django/                # Django 数据接口
    |-- frontend/              # Vue 前端
    `-- springboot/            # Spring Boot 用户服务
```

本机 `packages/cache/frontend-node-modules-old` 是整理前已有的前端依赖备份，不参与启动，也不会提交到 Git。正常前端依赖可通过 `npm ci` 重新安装。

## 环境要求

- Windows 10/11 与 PowerShell 5.1+
- MySQL 8.x，默认监听 `3306`
- Python 3.11（通过 Windows `py` 启动器调用）
- JDK 11、Maven 3.8+
- Node.js 18+、npm

首次运行前，在项目根目录安装依赖：

```powershell
py -3.11 -m pip install -r .\config\requirements-windows.txt
npm --prefix .\src\frontend ci
```

Maven 会在首次启动 Spring Boot 时自动下载 Java 依赖。

## 数据库配置

先复制公开模板并填写本机值：

```powershell
Copy-Item .\config\environment.example.ps1 .\config\local.env.ps1
```

`config/local.env.ps1` 已被 Git 忽略，一键脚本会自动加载它。不要将该文件、真实密码或密钥提交到仓库。

三个后端共用以下环境变量：

| 环境变量 | 默认值或要求 |
|---|---|
| `STRESS_DB_HOST` | `localhost` |
| `STRESS_DB_PORT` | `3306` |
| `STRESS_DB_USER` | `stress_app` |
| `STRESS_DB_PASSWORD` | 必填，不提供默认值 |
| `STRESS_DB_NAME` | `stress_db` |
| `DJANGO_SECRET_KEY` | 必填，使用独立随机值 |
| `STRESS_JWT_SECRET` | 必填，至少 32 个随机字节 |
| `STRESS_ADMIN_PASSWORD` | 首次创建管理员时设置；创建后可删除该项 |

生产环境应使用最小权限数据库账号，并关闭 `STRESS_DJANGO_DEBUG`。

## 一键启动

先启动 MySQL，再从项目根目录运行：

```powershell
.\scripts\start.ps1
```

脚本会依次创建或补全数据库表、执行 Django 迁移，并启动三个服务。启动完成后访问：

- 前端：<http://127.0.0.1:5173>
- Django API：<http://127.0.0.1:8000/api/>
- Spring Boot API：<http://127.0.0.1:8080/api/>

日志写入 `logs`。如果数据库已经初始化并且只需重启服务：

```powershell
.\scripts\start.ps1 -SkipDatabaseUpdate
```

停止由一键脚本启动的服务：

```powershell
.\scripts\stop.ps1
```

## 分别启动

```powershell
# 单独启动前先将私有配置载入当前会话
. .\config\local.env.ps1

# Django，端口 8000
py -3.11 .\scripts\run_django.py

# Spring Boot，端口 8080
mvn -s .\config\maven-settings.xml -f .\src\springboot\pom.xml spring-boot:run

# Vue，端口 5173
npm --prefix .\src\frontend run dev -- --host 127.0.0.1
```

只更新数据库结构：

```powershell
.\scripts\update_database.ps1
```

## 运行本地分析脚本

本地 pandas/scikit-learn 脚本默认读取 `data/raw`，结果写入上面配置的 MySQL 数据库：

```powershell
py -3.11 .\src\analytics\run_ml_models.py
py -3.11 .\src\analytics\gen_classification.py
```

可用 `STRESS_DATA_DIR` 指向另一套 CSV 目录：

```powershell
$env:STRESS_DATA_DIR = 'D:\data\fitbit'
py -3.11 .\src\analytics\run_ml_models.py
```

`src/analytics/stress_analysis.py` 是 CentOS/Spark 版本，默认读取 HDFS 的 `/stress/input/`，并将结果写入可从虚拟机访问的 MySQL。离线安装文件保存在 `packages`，详细环境与模型说明见 [项目介绍](docs/project-overview.md) 和 [开发记录](docs/project-progress.md)。

## 仓库数据策略

`.gitignore` 会排除原始健康数据、私有环境配置、运行日志、依赖目录、离线安装包和构建产物。`data/raw/README.md` 只记录本地需要的文件名，不包含数据内容或用户标识。

## 验证与构建

```powershell
# Django 配置检查
py -3.11 .\scripts\run_django.py check

# Spring Boot 测试
mvn -s .\config\maven-settings.xml -f .\src\springboot\pom.xml test

# Vue 生产构建
npm --prefix .\src\frontend run build
```

更多说明见 [文档索引](docs/README.md)。
