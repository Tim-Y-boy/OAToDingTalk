# 钉钉知识库文件上传服务

接收 OA 系统推送的 PDF 文件，自动上传到钉钉知识库，并按日期归档到对应文件夹。

## 功能特性

- 📥 提供两个上传接口：文件流直传 / URL 下载转传
- 📅 按日期自动归档（支持按月 `2026-06` 或按天 `2026-06-12`）
- 🔁 钉钉 access_token 自动获取与定时刷新（每 110 分钟）
- 🔒 简单 API Key 鉴权
- 📝 loguru 日志，按天滚动

## 技术栈

- **FastAPI** + **Uvicorn** — Web 框架
- **httpx** — 异步 HTTP 客户端（调用钉钉 API）
- **pydantic-settings** — 配置管理
- **APScheduler** — 定时刷新 Token
- **loguru** — 日志

## 目录结构

```
dingtalk-knowledge-service/
├── app/
│   ├── main.py              # 入口、定时任务、生命周期
│   ├── config.py            # 配置项（读 .env）
│   ├── models.py            # 请求/响应模型
│   ├── routers/upload.py    # 上传接口与编排逻辑
│   ├── services/
│   │   ├── token.py         # access_token 管理
│   │   ├── dingtalk.py      # 钉钉存储 API（上传/移动/重命名）
│   │   └── folder.py        # 日期文件夹管理
│   ├── utils/http.py        # httpx 客户端封装
│   └── doc/                 # 文档
│       ├── 技术方案.md
│       └── OA对接接口文档.md
├── .env.example             # 配置模板
└── requirements.txt
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制模板并填写：

```bash
cp .env.example .env
```

编辑 `.env`：

```ini
# 钉钉应用凭证
DINGTALK_APP_KEY=你的AppKey
DINGTALK_APP_SECRET=你的AppSecret

# 钉钉知识库配置
DINGTALK_SPACE_ID=知识库workspaceId
DINGTALK_ROOT_DENTRY_UUID=知识库根目录rootNodeId
DINGTALK_ADMIN_UNION_ID=操作人unionId

# 文件夹命名规则: month=按月  day=按天
FOLDER_FORMAT=month

# OA 调用本服务的鉴权 Key
API_KEY=自定义一个密钥

# 服务端口
PORT=8000
```

> ⚠️ `.env` 含密钥，已在 `.gitignore` 中排除，请勿提交。

### 3. 所需钉钉权限

应用需在钉钉开放平台开通以下权限：

- `Wiki.Workspace.Read` — 读取知识库列表
- `Storage.UploadInfo.Read` — 获取上传信息
- `Storage.File.Write` — 提交文件

权限申请并**发布新版本**后生效。

### 4. 启动

```bash
python -m app.main
```

启动后访问 `http://localhost:8000/docs` 可查看交互式 API 文档。

## 接口一览

| 接口 | 方法 | 路径 | 说明 |
|---|---|---|---|
| 健康检查 | GET | `/api/health` | 服务状态与 Token 有效性 |
| 文件流上传 | POST | `/api/upload/file` | 直接上传 PDF 文件 |
| URL 上传 | POST | `/api/upload/url` | 提供 PDF 下载地址 |

完整的请求/响应格式、字段说明、错误码见 👉 [OA 对接接口文档](app/doc/OA对接接口文档.md)

## 上传流程说明

钉钉 alidocs 知识库的存储接口有两个限制：子目录直传会报 500、文件名会被系统改写为数字。
因此上传采用四步完成：

1. **上传到根目录** → 获取文件 ID 与空间 ID
2. **建/复用日期文件夹** → 按月或按天命名
3. **移动文件进文件夹** → `move`
4. **重命名为正确文件名** → `rename`（同名自动加后缀）

## 配置项说明

| 变量 | 说明 |
|---|---|
| `DINGTALK_APP_KEY` / `DINGTALK_APP_SECRET` | 钉钉应用凭证 |
| `DINGTALK_SPACE_ID` | 知识库 workspaceId |
| `DINGTALK_ROOT_DENTRY_UUID` | 知识库根目录 rootNodeId（作为上传 parentDentryUuid） |
| `DINGTALK_ADMIN_UNION_ID` | 执行操作的用户 unionId（需有知识库权限） |
| `FOLDER_FORMAT` | 文件夹粒度：`month` / `day` |
| `API_KEY` | OA 调用时的鉴权密钥 |
| `PORT` | 服务端口，默认 8000 |
