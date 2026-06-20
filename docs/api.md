# 200iq-moments API

本服务是本地运行的错误案例结构化记忆库，默认地址：

```bash
http://127.0.0.1:8200
```

## 启动

开发启动：

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8200 --reload
```

Docker Compose 启动：

```bash
docker compose up --build
```

## 通用错误格式

```json
{
  "error": {
    "code": "CASE_NOT_FOUND",
    "message": "Case not found: 999",
    "details": {}
  }
}
```

## System

### GET `/v1/health`

健康检查。

### GET `/v1/info`

返回服务名称、描述、API 版本、案例数量、存储类型和鉴权开关状态。

## Templates

### GET `/v1/templates/case`

返回 Case JSON 模板，包括必填字段、可选字段、枚举值和字段结构。

### GET `/v1/templates/case/markdown`

返回 Markdown 模板内容。

## Cases

### POST `/v1/cases/validate`

校验 Case JSON，不写入文件。

请求：

```json
{
  "title": "机场套餐误判",
  "date": "2025-06-20",
  "summary": "看到单位价格划算就下单。",
  "reality": "套餐一个月过期。",
  "avoidance": ["确认有效期"],
  "checklist": ["有效期是多久？"]
}
```

### POST `/v1/cases/preview`

把 Case JSON 渲染为 Markdown，不写入文件。

### GET `/v1/cases`

返回案例列表。

支持查询参数：

```text
status=published|draft|archived|deleted
loss_type=money|time|dignity|opportunity|energy|other
tag=subscription
q=机场
from=2025-01-01
to=2025-12-31
limit=20
offset=0
sort=date_desc|date_asc|created_desc|updated_desc
```

### POST `/v1/cases`

创建 Case，服务端生成 `id` 和 `slug`，并写入 Markdown 文件。

### GET `/v1/cases/{case_id}`

返回完整 Case JSON。

### PATCH `/v1/cases/{case_id}`

局部更新 Case。

### DELETE `/v1/cases/{case_id}`

默认归档 Case。可用 `mode=delete` 设置软删除状态。

### GET `/v1/cases/{case_id}/markdown`

返回单个 Case 的 Markdown 内容。

## Import / Export

### POST `/v1/import/markdown`

从 Markdown 导入 Case。

请求：

```json
{
  "content": "## Case Study #001 — 机场套餐误判\n...",
  "mode": "upsert"
}
```

### GET `/v1/export/json`

导出 Case JSON。可用 `status=published` 过滤状态。

### GET `/v1/export/markdown`

导出 Case Markdown。

## Stats

### GET `/v1/stats/summary`

返回总案例数、状态分布、累计损失、损失类型分布、标签排行和最新案例日期。

### GET `/v1/stats/timeline`

按月份返回案例数量和损失金额。

## Index

### POST `/v1/index/sync`

按更新时间返回案例变更事件。

请求：

```json
{
  "since": "2025-01-01T00:00:00+08:00"
}
```

### POST `/v1/index/rebuild`

返回可用于重建索引的案例文本和元数据。
