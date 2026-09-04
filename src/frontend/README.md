# Stress Analysis Frontend

压力检测数据分析系统的 Vue 3 前端，使用 Vite、Element Plus、ECharts、Axios 和 Vue Router。

## 本地运行

从项目根目录执行：

```powershell
npm --prefix .\src\frontend ci
npm --prefix .\src\frontend run dev -- --host 127.0.0.1
```

前端默认访问 `http://127.0.0.1:5173`，并连接：

- Django 数据 API：`http://127.0.0.1:8000/api`
- Spring Boot 用户 API：`http://127.0.0.1:8080/api`

## 构建与检查

```powershell
npm --prefix .\src\frontend run build
npm --prefix .\src\frontend run lint
```

完整环境配置及一键启动方式见项目根目录的 `README.md`。
