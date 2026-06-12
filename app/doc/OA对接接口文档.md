# OA 对接接口文档 — 钉钉知识库文件上传服务

> 本服务接收 OA 系统推送的 PDF 文件，自动上传到钉钉知识库，并按日期归档到对应文件夹。

---

## 1. 基本信息

| 项 | 值 |
|---|---|
| Base URL | `http://<服务IP>:8000` |
| 协议 | HTTP |
| 请求编码 | UTF-8 |
| 鉴权方式 | 请求头 `X-API-Key` |

### 1.1 鉴权

所有上传接口需在请求头携带 API Key：

```
X-API-Key: <约定的密钥>
```

> ⚠️ 若 OA 侧不使用鉴权，请联系服务维护方确认该密钥值（当前占位值为 `no-auth`，即请求头传 `X-API-Key: no-auth`）。

### 1.2 归档规则

- 文件按**日期**归档到知识库对应文件夹。
- 文件夹命名由服务端配置决定：
  - `month` 模式 → 文件夹名如 `2026-06`
  - `day` 模式 → 文件夹名如 `2026-06-12`
- 同一日期文件夹不存在时自动创建；同名文件自动追加 `(1)`、`(2)` 后缀，**不会覆盖**。

---

## 2. 接口列表

| 接口 | 方法 | 路径 | 说明 |
|---|---|---|---|
| 健康检查 | GET | `/api/health` | 检查服务状态与 Token 有效性 |
| 文件流上传 | POST | `/api/upload/file` | 直接上传 PDF 文件内容 |
| URL 上传 | POST | `/api/upload/url` | 提供 PDF 下载地址，由服务端下载后上传 |

---

## 3. 接口详情

### 3.1 健康检查

`GET /api/health`

**用途**：联调前先调用此接口确认服务可达、钉钉 Token 有效。

**请求示例**：
```bash
curl http://<服务IP>:8000/api/health
```

**响应示例**：
```json
{
  "status": "ok",
  "token_valid": true,
  "token_expire_at": "2026-06-12 13:08:11"
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| status | string | 固定 `ok` |
| token_valid | bool | 钉钉 access_token 是否有效 |
| token_expire_at | string | Token 过期时间 |

---

### 3.2 文件流上传（推荐）

`POST /api/upload/file`

**Content-Type**：`multipart/form-data`

**用途**：OA 直接把 PDF 文件本体推过来，适合 OA 能直接读到本地文件的场景。

**请求参数（form-data）**：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| file | File | 是 | PDF 文件（multipart 文件流） |
| name | string | 否 | 文件名（含后缀），不传则用上传文件的原名；不带 `.pdf` 会自动补 |
| date | string | 否 | 归档日期，格式 `YYYY-MM-DD`，如 `2026-06-12`；不传默认当天 |

**请求示例**：
```bash
curl -X POST http://<服务IP>:8000/api/upload/file \
  -H "X-API-Key: no-auth" \
  -F "file=@/path/to/report.pdf" \
  -F "name=失效分析报告_20260612.pdf" \
  -F "date=2026-06-12"
```

**响应示例（成功）**：
```json
{
  "success": true,
  "dentry_uuid": "ZgpG2NdyVXrOD0XptGz1w7b68MwvDqPk",
  "folder": "2026-06",
  "file_name": "失效分析报告_20260612.pdf",
  "message": ""
}
```

**响应示例（失败）**：
```json
{
  "success": false,
  "dentry_uuid": "",
  "folder": "",
  "file_name": "",
  "message": "文件超过100MB限制"
}
```

---

### 3.3 URL 上传

`POST /api/upload/url`

**Content-Type**：`application/json`

**用途**：OA 只能提供文件下载地址，由本服务先下载再上传到钉钉。要求该 URL 可被服务端公网访问。

**请求参数（JSON Body）**：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| file_url | string | 是 | PDF 下载地址（需服务端可访问，建议 HTTPS） |
| file_name | string | 是 | 文件名（含后缀），不带 `.pdf` 会自动补 |
| date | string | 否 | 归档日期 `YYYY-MM-DD`，不传默认当天 |

**请求示例**：
```bash
curl -X POST http://<服务IP>:8000/api/upload/url \
  -H "X-API-Key: no-auth" \
  -H "Content-Type: application/json" \
  -d '{
    "file_url": "https://oa.example.com/files/report.pdf",
    "file_name": "失效分析报告_20260612.pdf",
    "date": "2026-06-12"
  }'
```

**响应**：同 3.2。

---

## 4. 统一响应字段说明

| 字段 | 类型 | 说明 |
|---|---|---|
| success | bool | `true`=上传成功，`false`=失败（看 message） |
| dentry_uuid | string | 成功时返回钉钉文件标识；失败为空 |
| folder | string | 成功时返回归档到的文件夹名，如 `2026-06` |
| file_name | string | 实际落库文件名（重名时可能带后缀） |
| message | string | 失败原因；成功为空 |

---

## 5. 注意事项

1. **文件类型**：仅支持 PDF。文件名不带 `.pdf` 后缀时会自动补上。
2. **文件大小**：单文件上限 **100MB**。
3. **文件名编码**：请使用 **UTF-8** 编码（中文文件名正常支持）。⚠️ Windows 下用 curl 发中文表单字段会变乱码，建议用 Postman 或代码以 UTF-8 发送。
4. **文件名特殊字符**：不可包含 `* " < > |`，不能以 `.` 结尾。
5. **URL 上传**：`file_url` 必须是本服务可公网访问的地址；若需要鉴权下载，请使用带签名/Token 的直链。
6. **`date` 字段**：决定归档到哪个文件夹，传 OA 的业务日期即可，不传默认当天。
7. **响应判断**：以 HTTP 状态码 **200** 且 `success=true` 为成功依据。

---

## 6. 错误码

服务统一返回 HTTP 200，通过响应体 `success` 字段区分成败。常见失败原因：

| message | 原因 |
|---|---|
| 文件内容为空 | 上传了空文件 |
| 文件超过100MB限制 | 超过单文件大小上限 |
| 文件下载失败: ... | URL 上传时下载不到文件 |
| 无效的 API Key | 请求头 `X-API-Key` 不正确（HTTP 401） |
| 钉钉API错误: ... | 调用钉钉接口异常，看具体信息 |

---

## 7. 联调建议

1. 先调 `GET /api/health` 确认服务在线、Token 有效。
2. 用一个测试 PDF 调 `/api/upload/file`，确认返回 `success=true`。
3. 到钉钉知识库对应日期文件夹确认文件已归档、文件名正确。
4. 切换到 `/api/upload/url` 验证 OA 提供的下载链路。
