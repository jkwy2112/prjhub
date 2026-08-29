# PrjHub · 轻量级项目管理系统

参考 Jira / TAPD / Worktile 的核心工作流实现的小型项目管理系统: 项目 → 任务 → 看板 → 动态, 内置 **LDAP** 与 **企业微信** 集中认证, 项目创建时可**自动初始化服务端 Git 仓库**。

## 功能特性

| 模块 | 说明 |
| --- | --- |
| 认证 | 本地账号密码( PBKDF2 ); LDAP 域账号( 搜索-绑定 校验, 首登自动建号 ); 企业微信网页授权( OAuth2 + 自动同步姓名/邮箱/头像 ) |
| 项目 | 项目标识(KEY) → 任务编号 (`PRJ-12`), 成员角色( 所有者/管理员/成员 ), 归档, 颜色标签 |
| 任务 | 类型( 需求/任务/缺陷 ), 优先级, 负责人, 截止日期, 状态工作流( 待办→进行中→测试中→已完成, 非法流转会被拒绝 ) |
| 看板 | 四列拖拽移动( HTML5 Drag & Drop ), 卡片展示类型/优先级/评论数/逾期标记 |
| 协作 | 任务评论, 项目动态时间线, 个人仪表盘( 统计卡片 + 状态分布图 + 待办列表 ) |
| 管理面板 | 超管后台: 系统概览( 用户/项目/任务/Git 仓库统计, 认证方式状态 ), 用户管理( 创建/编辑/禁用/重置密码/授权超管 ) |
| BPMN 审批流 | 基于 **SpiffWorkflow**( Python BPMN 2.0 引擎 ): 多级审批链、条件网关自动路由、会签/或签( multi-instance + 完成条件, 满足即自动终止剩余实例 )、流程定义版本化( 在途实例锁定旧版 )、审批单中途持久化( 引擎状态序列化落库 )、审批中心( 我的待办/我发起的/时间线/撤回 ) |
| Git | 创建项目时自动 `git init --bare` 初始化空仓库, 删除项目时同步清理; 也可事后补建 |

## 架构

```
┌─────────────────────────┐        ┌──────────────────────────────┐
│  frontend (Vue3+EP)     │  /api  │  backend (FastAPI)           │
│  登录/仪表盘/看板/列表   │ ─────► │  JWT 鉴权                    │
│  成员/动态/设置          │  proxy │  ├─ services/ldap    ← LDAP 服务器
└─────────────────────────┘        │  ├─ services/wecom   ← 企业微信 API
                                   │  ├─ services/git     ← git init --bare
                                   │  └─ SQLAlchemy ──► SQLite / PostgreSQL
                                   └──────────────────────────────┘
```

## 快速开始

要求: Python 3.9+, Node.js 18+, git; 数据库使用 PostgreSQL (Docker 一键启动)

```bash
# 0) 数据库
docker compose up -d db            # PostgreSQL 16, 端口 5432, 库 prjhub

# 1) 后端
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env               # 默认连接本机 Docker PostgreSQL
.venv/bin/uvicorn app.main:app --reload --port 8000

# 2) 前端 (另开终端)
cd frontend
npm install
npm run dev                        # http://localhost:5173  (/api 已代理到 8000)
```

首次启动自动创建管理员 `admin / admin123` 和示例项目 DEMO ( 生产环境务必修改 `.env` 中的 `ADMIN_PASSWORD` 与 `SECRET_KEY` )。也可将 `DATABASE_URL` 改回 SQLite ( `sqlite:///./data/prjhub.db` ) 零依赖运行。

## 认证配置

### LDAP

```ini
LDAP_ENABLED=true
LDAP_SERVER=ldap://ldap.example.com:389
LDAP_BIND_DN=cn=admin,dc=example,dc=com        # 服务账号, 用于搜索
LDAP_BIND_PASSWORD=****
LDAP_SEARCH_BASE=ou=people,dc=example,dc=com
LDAP_SEARCH_FILTER=(uid={login})               # AD 环境用 (sAMAccountName={login})
```

登录流程: 本地校验失败后自动尝试 LDAP → 服务账号搜索用户 DN → 以该 DN + 密码二次绑定验证 → 首次成功登录自动建号并同步姓名/邮箱。

### 企业微信

```ini
WECOM_ENABLED=true
WECOM_CORP_ID=ww***************
WECOM_CORP_SECRET=************
WECOM_AGENT_ID=1000002
```

登录页出现"企业微信登录"按钮 → 跳转授权 (scope=snsapi_base) → 回调携带 code → 后端换取 userid 并拉取通讯录资料 → 自动建号/登录。测试套件中已包含 LDAP 与企业微信的 mock 用例。

## Git 仓库

- 创建项目勾选"自动初始化空仓库"后, 服务端执行 `git init --bare -b main repos/{KEY}.git`
- 项目「设置」页展示仓库路径与克隆地址, 支持事后补建与随项目删除
- 当前作为独立的代码仓托管入口; 可按需扩展 git-http-backend / SSH 提供 push/pull

## API 一览 ( 完整文档见 http://localhost:8000/docs )

```
POST /auth/login            账号密码登录(本地, 失败自动尝试LDAP)
POST /auth/wecom            企业微信授权码登录
GET  /auth/wecom/url        获取企业微信授权跳转地址
GET  /auth/me               当前用户
GET  /projects              我参与的项目 / POST 创建(自动init仓库)
PUT  /projects/{id}         更新 / DELETE 删除(含任务与仓库)
POST /projects/{id}/init-repo           补建 Git 仓库
GET|POST /projects/{id}/members         成员管理
GET  /projects/{id}/activities          项目动态
GET|POST /projects/{id}/tasks           任务列表/创建
GET|PUT|DELETE /tasks/{id}              任务详情/更新(状态流转校验)/删除
POST /tasks/{id}/comments               评论
GET  /my/tasks               我的任务
GET  /dashboard              仪表盘统计
GET  /admin/stats            系统概览( 超管 )
GET|POST /admin/users        用户列表/创建( 超管 )
PUT  /admin/users/{id}       编辑/禁用/重置密码/授权超管( 超管 )
```

## 测试

```bash
cd backend && .venv/bin/python -m pytest tests/ -q      # 42 个用例 (默认 SQLite, Python 3.11+)
# 在 PostgreSQL 上跑同一套测试:
TEST_DATABASE_URL=postgresql+psycopg2://prjhub:prjhub_secret@127.0.0.1:5432/prjhub_test \
  .venv/bin/python -m pytest tests/ -q
cd frontend && npm run build                            # 构建校验
```

## BPMN 审批流( SpiffWorkflow )

引擎访问被隔离在 `app/services/bpmn_engine.py` 单一适配层, 业务代码不直接依赖引擎 API, 未来可替换引擎。

- 内置「通用审批流」模板: 一级审批 → (驳回即结束) → 金额条件网关 → 大额走会签( N 人并行, 2 人通过即通过并自动终止其余实例 ) / 小额走二级审批
- 流程变量约定: `amount`( 金额条件 )、`approver_l1` / `approver_l2`( 各级审批人 user id )、`countersigners`( 会签人列表 )、`cs_total` / `cs_pass`
- 每次审批动作 = 反序列化引擎状态 → 注入变量( approved/rejected/completed_count ) → 推进 → 重新序列化落库; 待办/历史通过 `approval_tasks` 镜像表同步
- 部署新 BPMN 自动生成新版本, 在途审批单锁定其发起时版本跑完 ( 旧版跑完策略 )

## 目录结构

```
prjuse/
├── backend/
│   ├── app/
│   │   ├── core/        # 配置 / JWT / 密码哈希
│   │   ├── routers/     # auth users projects tasks dashboard
│   │   ├── services/    # ldap_service wecom_service git_service auth_service
│   │   ├── models.py    # User Project ProjectMember Task Comment Activity
│   │   └── main.py      # 应用工厂 + 种子数据
│   └── tests/           # pytest (外部认证全部 mock)
├── frontend/
│   └── src/
│       ├── views/       # Login Dashboard Projects ProjectDetail MyTasks
│       ├── components/  # TaskDialog TaskDrawer
│       ├── layouts/     # MainLayout
│       └── stores/      # pinia auth
└── README.md
```
