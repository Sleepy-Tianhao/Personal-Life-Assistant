# Personal Life Assistant API 契约

版本：`v1`  
Base URL：`http://127.0.0.1:8000`  
API 前缀：`/api/v1`  
在线文档：`/docs`（Swagger UI）、`/redoc`、`/openapi.json`  
仓库内快照：[`openapi.json`](openapi.json)

## 1. 通用约定

### 1.1 使用场景

这是本地单用户、无登录的应用后端。默认只应监听 `127.0.0.1`，不要直接暴露到公网。

### 1.2 数据格式

- 除课表导入外，请求与响应均为 JSON，字符编码 UTF-8；课表导入使用 `multipart/form-data`。
- 时间字段使用 ISO 8601 字符串。后端统一以 UTC 存储和返回，例如 `2026-10-31T08:00:00Z`。
- 传入不带时区的时间会被当作 UTC；推荐前端使用 `Date.toISOString()` 或明确传入偏移量，例如 `2026-10-31T16:00:00+08:00`。
- 日记的 `entry_date` 是日期（`YYYY-MM-DD`），不是时间点。
- 课表的 `start_time` / `end_time` 是校园本地时间，不做 UTC 转换。
- 金额统一使用整数分（minor unit），字段名以 `_cents` 结尾。例如 12.50 元传 `1250`，避免浮点误差。
- 所有资源 ID 为正整数。

### 1.3 分页

列表接口统一返回：

```json
{
  "items": [],
  "total": 0,
  "limit": 50,
  "offset": 0
}
```

参数：

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `limit` | `50` | 每页数量，范围 1–200 |
| `offset` | `0` | 偏移量，从 0 开始 |

### 1.4 错误格式

除 FastAPI 自动生成的 422 校验错误外，业务错误格式为：

```json
{"detail": "Todo not found"}
```

| 状态码 | 含义 |
| --- | --- |
| `400` | 当前接口未使用 |
| `404` | 资源不存在 |
| `409` | 冲突，例如同一天创建两篇日记 |
| `422` | 参数校验失败、时间范围非法、日程结束时间不晚于开始时间 |

### 1.5 时间范围规则

- 账目 `start_at` / `end_at`：左闭右开 `[start_at, end_at)`，适合按自然月查询。
- 日程 `range_start` / `range_end`：左闭右开区间，返回与该区间有重叠的日程。
- 待办 `due_from` / `due_to`：闭区间 `[due_from, due_to]`。
- 日记 `start_date` / `end_date`：闭区间。

---

## 2. 系统接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/health` | 健康检查，返回 `{"status":"ok"}` |
| `GET` | `/` | 服务名称、版本与文档地址 |
| `GET` | `/docs` | Swagger UI |
| `GET` | `/openapi.json` | OpenAPI 3 规范 |

---

## 3. TodoList

路径前缀：`/api/v1/todos`

### 3.1 数据字段

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `id` | integer | 响应 | 主键 |
| `title` | string(1–200) | 创建必填 | 标题，自动去除首尾空白 |
| `description` | string(≤5000) / null | 否 | 描述 |
| `status` | enum | 否 | `pending`、`in_progress`、`completed`，默认 `pending` |
| `priority` | enum | 否 | `low`、`medium`、`high`，默认 `medium` |
| `due_at` | datetime / null | 否 | 截止时间 |
| `completed_at` | datetime / null | 响应 | 完成时间，由后端维护 |
| `is_overdue` | boolean | 响应 | 未完成且已过截止时间时为 `true` |
| `created_at` | datetime | 响应 | 创建时间 |
| `updated_at` | datetime | 响应 | 更新时间 |

将 `status` 改为 `completed` 时，后端自动填写 `completed_at`；改回非完成状态时自动清空。

### 3.2 接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/api/v1/todos` | 列表/搜索 |
| `POST` | `/api/v1/todos` | 创建，`201` |
| `GET` | `/api/v1/todos/{todo_id}` | 详情 |
| `PATCH` | `/api/v1/todos/{todo_id}` | 部分更新 |
| `DELETE` | `/api/v1/todos/{todo_id}` | 删除，`204` |

`GET /api/v1/todos` 查询参数：

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| `status` | string，可重复 | 多状态过滤，如 `?status=pending&status=in_progress` |
| `priority` | string，可重复 | 多优先级过滤 |
| `search` | string | 搜索标题和描述 |
| `due_from` | datetime | 截止时间下界，闭区间 |
| `due_to` | datetime | 截止时间上界，闭区间 |
| `sort_by` | enum | `created_at`、`updated_at`、`due_at`，默认 `created_at` |
| `sort_order` | enum | `asc`、`desc`，默认 `desc` |
| `limit` / `offset` | integer | 分页 |

创建示例：

```json
{
  "title": "写周报",
  "description": "总结本周进度",
  "priority": "high",
  "due_at": "2026-10-31T18:00:00+08:00"
}
```

更新示例：

```json
{"status": "completed"}
```

清空截止时间：

```json
{"due_at": null}
```

---

## 4. 记账

路径前缀：`/api/v1/ledger`

### 4.1 数据字段

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `id` | integer | 响应 | 主键 |
| `type` | enum | 是 | `income`（收入）、`expense`（支出） |
| `amount_cents` | integer | 是 | 金额，正整数，单位分 |
| `category` | string(1–50) | 是 | 分类，例如“餐饮”“工资” |
| `note` | string(≤500) / null | 否 | 备注 |
| `occurred_at` | datetime | 否 | 发生时间，创建时默认为当前 UTC 时间 |
| `created_at` | datetime | 响应 | 创建时间 |
| `updated_at` | datetime | 响应 | 更新时间 |

### 4.2 接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/api/v1/ledger/transactions` | 流水列表/搜索 |
| `POST` | `/api/v1/ledger/transactions` | 创建，`201` |
| `GET` | `/api/v1/ledger/transactions/{id}` | 详情 |
| `PATCH` | `/api/v1/ledger/transactions/{id}` | 部分更新 |
| `DELETE` | `/api/v1/ledger/transactions/{id}` | 删除，`204` |
| `GET` | `/api/v1/ledger/summary` | 汇总与分组统计 |

流水列表参数：

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| `type` | enum | `income` / `expense` |
| `category` | string | 分类精确匹配 |
| `start_at` | datetime | 发生时间下界（包含） |
| `end_at` | datetime | 发生时间上界（不包含） |
| `search` | string | 搜索分类和备注 |
| `sort_by` | enum | `occurred_at`、`amount_cents`、`created_at`，默认 `occurred_at` |
| `sort_order` | enum | `asc` / `desc`，默认 `desc` |
| `limit` / `offset` | integer | 分页 |

汇总参数与流水列表相同，另支持：

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| `group_by` | enum | `category` 或 `type`；不传则不分组 |

汇总响应：

```json
{
  "start_at": "2026-08-01T00:00:00Z",
  "end_at": "2026-09-01T00:00:00Z",
  "income_cents": 100000,
  "expense_cents": 4000,
  "balance_cents": 96000,
  "transaction_count": 3,
  "groups": [
    {
      "key": "工资",
      "income_cents": 100000,
      "expense_cents": 0,
      "balance_cents": 100000,
      "count": 1
    }
  ]
}
```

创建示例：

```json
{
  "type": "expense",
  "amount_cents": 2500,
  "category": "餐饮",
  "note": "午饭",
  "occurred_at": "2026-10-31T12:30:00+08:00"
}
```

按 2026 年 8 月（北京时间）统计：

```text
GET /api/v1/ledger/summary?start_at=2026-08-01T00:00:00%2B08:00&end_at=2026-09-01T00:00:00%2B08:00&group_by=category
```

---

## 5. 日程

路径前缀：`/api/v1/schedules`

### 5.1 数据字段

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `id` | integer | 响应 | 主键 |
| `title` | string(1–200) | 是 | 标题 |
| `description` | string(≤5000) / null | 否 | 描述 |
| `location` | string(≤200) / null | 否 | 地点 |
| `start_at` | datetime | 是 | 开始时间 |
| `end_at` | datetime | 是 | 结束时间，必须晚于 `start_at` |
| `all_day` | boolean | 否 | 是否全天，默认 `false` |
| `created_at` | datetime | 响应 | 创建时间 |
| `updated_at` | datetime | 响应 | 更新时间 |

`all_day` 只是标记，开始/结束时间仍需由前端设置为当天边界。当前版本不包含重复日程和提醒推送。

### 5.2 接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/api/v1/schedules` | 列表/按时间区间查询 |
| `POST` | `/api/v1/schedules` | 创建，`201` |
| `GET` | `/api/v1/schedules/{schedule_id}` | 详情 |
| `PATCH` | `/api/v1/schedules/{schedule_id}` | 部分更新 |
| `DELETE` | `/api/v1/schedules/{schedule_id}` | 删除，`204` |

列表参数：

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| `range_start` | datetime | 返回结束时间晚于该时刻的日程（`end_at > range_start`） |
| `range_end` | datetime | 返回开始时间早于该时刻的日程（`start_at < range_end`） |
| `search` | string | 搜索标题、描述、地点 |
| `sort_by` | enum | `start_at`、`end_at`、`created_at`，默认 `start_at` |
| `sort_order` | enum | `asc` / `desc`，默认 `asc` |
| `limit` / `offset` | integer | 分页 |

查询某天/某周日程时，前端应传本地时间的自然边界，例如：

```text
GET /api/v1/schedules?range_start=2026-10-31T00:00:00%2B08:00&range_end=2026-11-01T00:00:00%2B08:00
```

创建示例：

```json
{
  "title": "项目评审",
  "location": "会议室 A",
  "start_at": "2026-11-02T10:00:00+08:00",
  "end_at": "2026-11-02T11:00:00+08:00"
}
```

---

## 6. 日记

路径前缀：`/api/v1/diary`

### 6.1 数据字段

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `id` | integer | 响应 | 主键 |
| `entry_date` | date | 是 | 日记日期，全局唯一 |
| `title` | string(≤200) / null | 否 | 标题 |
| `content` | string(1–100000) | 是 | 正文，不可为空白 |
| `mood` | string(≤20) / null | 否 | 心情，建议使用固定枚举 |
| `weather` | string(≤20) / null | 否 | 天气 |
| `created_at` | datetime | 响应 | 创建时间 |
| `updated_at` | datetime | 响应 | 更新时间 |

同一天只能有一篇日记，重复创建或把另一篇改到同一天会返回 `409`。

### 6.2 接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/api/v1/diary/entries` | 列表/搜索 |
| `POST` | `/api/v1/diary/entries` | 创建，`201` |
| `GET` | `/api/v1/diary/entries/by-date/{entry_date}` | 按日期获取 |
| `GET` | `/api/v1/diary/entries/{entry_id}` | 按 ID 获取 |
| `PATCH` | `/api/v1/diary/entries/{entry_id}` | 部分更新 |
| `DELETE` | `/api/v1/diary/entries/{entry_id}` | 删除，`204` |

列表参数：

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| `start_date` | date | 起始日期，闭区间 |
| `end_date` | date | 结束日期，闭区间 |
| `mood` | string | 心情精确匹配 |
| `search` | string | 搜索标题和正文 |
| `sort_by` | enum | `entry_date`、`created_at`、`updated_at`，默认 `entry_date` |
| `sort_order` | enum | `asc` / `desc`，默认 `desc` |
| `limit` / `offset` | integer | 分页 |

创建示例：

```json
{
  "entry_date": "2026-10-31",
  "title": "十月的最后一天",
  "content": "今天完成了后端 API 的第一版。",
  "mood": "good",
  "weather": "晴"
}
```

---

## 7. 课表看板

路径前缀：`/api/v1/timetables`

### 7.1 导入文件格式

前端使用 `multipart/form-data` 上传 `.html` / `.htm` 文件，最大 2 MB。解析器按以下结构读取课程：

- 表格表头包含 `Time` 和星期列（Monday–Sunday，支持常见英文缩写和中文星期）；
- 每行是时间段，例如 `8.00am-9.00am`；
- 课程单元格可跨多行（`rowspan`），单元格内依次为：
  1. 课程代码
  2. 课程名称
  3. 教师
  4. 地点
  5. 可选周次，例如 `(Week 1-14)`；也支持 `Week 5`、`第1-14周`
- 周次缺失时，该课程视为所有周都适用。

导入只保存解析后的课程，不保存原始 HTML。若部分单元格无法解析，接口仍会导入可识别课程，并在 `warnings` 中返回原因；如果完全无法识别出课程，则返回 `422`。

### 7.2 数据字段

课表（Timetable）：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | integer | 主键 |
| `name` | string(≤200) | 课表名称 |
| `source_filename` | string(≤255) | 原始文件名 |
| `semester_start_date` | date / null | 第 1 周的起始日期，建议传周一 |
| `active` | boolean | 是否为当前激活课表 |
| `session_count` | integer | 课程节次数 |
| `created_at` / `updated_at` | datetime | 导入/更新时间 |

课程节次（CourseSession）：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | integer | 主键 |
| `weekday` | integer | 1=Monday … 7=Sunday |
| `start_time` / `end_time` | time | 本地时间，格式 `HH:MM:SS`，结束晚于开始 |
| `course_code` | string | 课程代码 |
| `course_name` | string | 课程名称 |
| `teacher` / `location` | string / null | 教师、地点 |
| `week_start` / `week_end` | integer / null | 适用周次闭区间 |

### 7.3 接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/api/v1/timetables` | 全部课表摘要，激活的排在前面 |
| `POST` | `/api/v1/timetables/import` | 导入 HTML 课表，`201` |
| `GET` | `/api/v1/timetables/active` | 当前激活课表及全部课程 |
| `GET` | `/api/v1/timetables/dashboard` | 课表看板 |
| `GET` | `/api/v1/timetables/{timetable_id}` | 指定课表及全部课程 |
| `PATCH` | `/api/v1/timetables/{timetable_id}` | 修改名称或学期开始日期 |
| `POST` | `/api/v1/timetables/{timetable_id}/activate` | 设为当前课表 |
| `DELETE` | `/api/v1/timetables/{timetable_id}` | 删除课表及课程，`204` |

导入表单字段：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `file` | file | 是 | `.html` / `.htm`，最大 2 MB |
| `name` | string | 否 | 课表名称，默认取文件名 |
| `semester_start_date` | date | 否 | 第 1 周起始日期 |
| `set_active` | boolean | 否 | 是否设为当前课表，默认 `true` |

导入示例：

```bash
curl -X POST http://127.0.0.1:8000/api/v1/timetables/import \
  -F "file=@/home/cufoflux/Downloads/202609 Semester Timetable.html;type=text/html" \
  -F "name=2026/09 Semester" \
  -F "semester_start_date=2026-09-07" \
  -F "set_active=true"
```

响应：

```json
{
  "timetable": {
    "id": 1,
    "name": "2026/09 Semester",
    "source_filename": "202609 Semester Timetable.html",
    "semester_start_date": "2026-09-07",
    "active": true,
    "session_count": 10,
    "sessions": [
      {
        "id": 1,
        "weekday": 1,
        "start_time": "16:00:00",
        "end_time": "18:00:00",
        "course_code": "ERA111",
        "course_name": "Python and Tensorflow Programming",
        "teacher": "Tony Hii Chang Soon",
        "location": "A3#602",
        "week_start": 1,
        "week_end": 14
      }
    ],
    "created_at": "2026-10-31T08:00:00Z",
    "updated_at": "2026-10-31T08:00:00Z"
  },
  "warnings": []
}
```

激活规则：

- 每次导入都会创建一份新课表，不会覆盖旧记录；需要替换时请删除旧课表；
- `set_active=true` 或调用激活接口时，会把其他课表设为非激活；
- 同一时间只有一个激活课表；
- 删除激活课表后不会自动选择新的课表，前端需要显式激活另一份。

### 7.4 课表看板

```text
GET /api/v1/timetables/dashboard?date=2026-09-09&timetable_id=1
```

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| `date` | date | 目标日期，默认服务器当天 |
| `timetable_id` | integer | 不传则使用当前激活课表 |

看板返回目标日期所在自然周（Monday–Sunday）的课程：

```json
{
  "timetable": {
    "id": 1,
    "name": "2026/09 Semester",
    "source_filename": "202609 Semester Timetable.html",
    "semester_start_date": "2026-09-07",
    "active": true,
    "session_count": 10,
    "created_at": "2026-10-31T08:00:00Z",
    "updated_at": "2026-10-31T08:00:00Z"
  },
  "date": "2026-09-09",
  "week_start_date": "2026-09-07",
  "week_end_date": "2026-09-13",
  "current_week": 1,
  "days": [
    {
      "weekday": 1,
      "weekday_name": "Monday",
      "date": "2026-09-07",
      "courses": []
    },
    {
      "weekday": 3,
      "weekday_name": "Wednesday",
      "date": "2026-09-09",
      "courses": []
    }
  ]
}
```

（上面的 `days` 仅为节选，实际始终包含完整的 7 天。）`current_week` 规则：

- 设置了 `semester_start_date`：以开始日期为第 1 周起点计算，1-based；
- 目标日期早于开始日期：返回 `0`，该周课程为空；
- 未设置 `semester_start_date`：返回 `null`，不做周次过滤，展示全部课程。

课程时间是本地时间，接口不做“当前课程/下一节课”判断；前端应使用本机时间与 `days[].courses` 自行高亮。

---

## 8. 后续接口边界

当前版本刻意不包含：

- 用户登录、多用户与权限；
- 多币种与汇率；
- 预算、账户余额、账单导入；
- 重复日程、日历订阅、提醒推送；
- 日记附件、图片、标签搜索；
- 课表手工编辑、单双周/多段周次规则、调课；
- 跨模块看板聚合接口。

数据库表由 SQLAlchemy `create_all` 初始化。进入前端联调后可补 Alembic；在正式发布前，数据库迁移策略需要固定下来。
