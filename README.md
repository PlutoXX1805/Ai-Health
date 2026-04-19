# 嗨 Hai（Hai）

医学人工智能课程项目：**嗨 Hai** 本地健康助手 — Streamlit + SQLite + 轻量 RAG + 体征规则预警；智能分析通过 **DeepSeek API**（OpenAI 兼容）提供服务。

> 仓库地址：<https://github.com/PlutoXX1805/Ai-Health>  
> 默认访问地址：**<http://127.0.0.1:8860>**（可在 `.streamlit/config.toml` 修改端口）

---

## 快速开始（克隆后本地运行）

### 0. 准备环境

- **Python 3.10+**（推荐 3.10 / 3.11，Windows 建议安装时勾选 *Add Python to PATH*）
- **Git**
- **DeepSeek API Key**：去 <https://platform.deepseek.com/> 申请，充值后复制密钥备用。

检查是否已安装：

```powershell
python --version
git --version
```

若 PowerShell 提示找不到 `python`，改用 `py --version`（Python Launcher），后续所有 `python` 命令都换成 `py` 即可。

### 1. 克隆仓库

```powershell
git clone https://github.com/PlutoXX1805/Ai-Health.git MedAi
cd MedAi
```

### 2. 创建并激活虚拟环境

Windows PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

> 若提示「**running scripts is disabled on this system**」，先在 PowerShell 里执行一次：  
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` 然后重开 PowerShell。

Windows CMD：

```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

macOS / Linux：

```bash
python3 -m venv .venv
source .venv/bin/activate
```

激活成功后命令行前会出现 `(.venv)` 前缀。

### 3. 安装依赖

```powershell
pip install -U pip
pip install -r requirements.txt
```

依赖清单见 `requirements.txt`（streamlit / pandas / requests / pypdf / python-dotenv / plotly / python-docx）。

### 4. 配置 DeepSeek 密钥

复制示例配置文件后填入自己的密钥（`.env` 已在 `.gitignore` 中，**不会**被提交）：

```powershell
copy .env.example .env     # Windows
# 或 cp .env.example .env   # macOS / Linux
```

用编辑器打开 `.env`，填写：

```dotenv
DEEPSEEK_API_KEY=sk-你自己的密钥
DEEPSEEK_MODEL=deepseek-chat
# 如需走代理可改：DEEPSEEK_API_BASE=https://api.deepseek.com
```

### 5. 启动应用

```powershell
streamlit run app.py
```

终端会打印访问地址，默认是 **<http://127.0.0.1:8860>**，浏览器一般会自动弹出。首次启动时 `hai_data.sqlite` 会自动在项目根目录生成（空库）。

想直接用测试数据体验，可在应用内上传：

- 示例检验报告：`data/samples/demo_report.txt`
- 示例体征数据：`data/samples/vitals_demo.csv`

### 6. 停止应用

在运行 Streamlit 的终端按 <kbd>Ctrl</kbd> + <kbd>C</kbd>。下次再跑时只要 `activate` 虚拟环境再 `streamlit run app.py` 即可。

---

## 常见问题（Windows 高频坑）

### A. `python` 不是内部或外部命令

安装时没勾选「Add Python to PATH」。可任选其一：

- 全部命令改用 **Python Launcher**：`py -m venv .venv`、`py -m pip install -r requirements.txt`、`py -m streamlit run app.py`
- 或在「设置 → 应用 → 应用执行别名」中关闭 `python.exe` / `python3.exe` 的商店重定向，然后重装 Python 并勾选 *Add to PATH*。

### B. 激活虚拟环境报「running scripts is disabled」

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

关闭 PowerShell 重开，再次执行 `.\.venv\Scripts\Activate.ps1`。

### C. 启动时提示「Port 8860 is not available」但 `netstat` 里没有进程

很多机器上 **Hyper-V / WSL / Docker** 会通过系统保留一段 TCP 端口。查看保留区间：

```powershell
netsh interface ipv4 show excludedportrange protocol=tcp
```

常见保留区间覆盖 **8441–8640**，因此 **8501、8510、8520、8601** 等会**无法绑定**。改用区间外的端口即可：

```powershell
streamlit run app.py --server.port 9005
```

也可以直接修改 `.streamlit/config.toml` 里的 `port`。

### D. 端口真被其它程序占用

关掉其它 Streamlit 终端或结束对应 `python` 进程后重试；或者换个端口（同上）。

### E. DeepSeek 调用失败 / 401 / 余额不足

- 确认 `.env` 中 `DEEPSEEK_API_KEY` 没写错、没多空格、没加引号。
- 登录 <https://platform.deepseek.com/> 查看余额与密钥状态。
- 公司 / 校园网代理阻断时，可挂全局代理，或改 `DEEPSEEK_API_BASE` 为可访问的兼容端点。
- 修改 `.env` 后需**重启** `streamlit run app.py` 才会生效。

### F. 首次运行问邮箱（Email）

直接 **回车留空** 即可，不必填写。减少 Streamlit 使用统计提示：本仓库的 `.streamlit/config.toml` 已设置 `gatherUsageStats = false`。

---

## 目录结构一览

```
MedAi/
├─ app.py                     # Streamlit 入口
├─ requirements.txt           # Python 依赖
├─ .env.example               # 环境变量模板（复制为 .env 后填写密钥）
├─ .streamlit/config.toml     # 端口 / 主题配置（默认 127.0.0.1:8860）
├─ core/                      # 业务模块：db / llm_client / rag / rules / 体征 / UI 样式 等
├─ data/
│  ├─ knowledge/              # RAG 本地知识片段（*.md）
│  └─ samples/                # 示例数据（demo_report.txt、vitals_demo.csv）
├─ Design/                    # 设计文档（可用 generate_design_doc.py 生成）
└─ hai_data.sqlite            # 运行时自动生成，已在 .gitignore 中
```

---

## 生成设计文档（可选）

需已安装依赖（含 `python-docx`），在项目根目录执行：

```powershell
py generate_design_doc.py
```

或双击运行 `generate_design_doc.bat`。输出：`Design/嗨Hai健康管理系统设计文档.docx`。

---

## Cursor：UI/UX Pro Max 技能（可选）

开源技能 [ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) 已接入本仓库：

- **Cursor 可读技能路径：** `.cursor/skills/ui-ux-pro-max/`（含 `SKILL.md`、`scripts/`、`data/`）。
- 完整上游克隆目录 `ui-ux-pro-max-skill/` 已列入 `.gitignore`，避免重复提交；需要更新时可自行 `git clone` 后同步 `scripts` 与 `data`。

界面主题与布局参考 **Wellness / Soft UI** 方向（医疗绿、浅底、卡片化指标），详见 `.streamlit/config.toml` 与 `core/ui_styles.py`。

---

## 协作与推送（维护者 / 队友）

本目录已是**独立 Git 仓库**（勿在用户主目录执行 `git add`，应在 `MedAi` 根目录操作）。

拉取最新代码：

```powershell
git pull origin main
```

提交 & 推送：

```powershell
git add .
git commit -m "feat: 你的改动说明"
git push origin main
```

> 首次向 GitHub 推送若提示认证，使用 **Personal Access Token** 代替密码，或配置 **Git Credential Manager**。  
> **切勿** 将 `.env`、`*.sqlite`、`.venv/` 提交到 Git（`.gitignore` 已覆盖）。

---

## License / 声明

本项目仅用于医学人工智能课程学习与演示，生成内容**不构成医疗建议**，如有健康问题请咨询专业医生。
