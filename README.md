# 嗨 Hai（Hai）

医学人工智能课程项目：**嗨 Hai** 本地健康助手 — Streamlit + SQLite + 轻量 RAG + 体征规则预警；智能分析通过 **DeepSeek API**（OpenAI 兼容）提供服务。

## DeepSeek API（推荐）

1. 复制项目根目录的 `.env.example` 为 `.env`。  
2. 在 `.env` 中填写：`DEEPSEEK_API_KEY=你的密钥`（**切勿**把密钥提交到 Git）。  
3. 重启 `streamlit run app.py`。

可选环境变量：`DEEPSEEK_MODEL`（默认 `deepseek-chat`）、`DEEPSEEK_API_BASE`（默认 `https://api.deepseek.com`）。

## Cursor：UI/UX Pro Max 技能

开源技能 [ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) 已接入本仓库：

- **Cursor 可读技能路径：** `.cursor/skills/ui-ux-pro-max/`（含 `SKILL.md`、`scripts/`、`data/`）。  
- 完整上游克隆目录 `ui-ux-pro-max-skill/` 已列入 `.gitignore`，避免重复提交；需要更新时可自行 `git clone` 后同步 `scripts` 与 `data`。

## 环境

- Python 3.10+

## 安装与运行

```bash
cd MedAi
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

浏览器访问终端里打印的地址。本项目默认 **`http://127.0.0.1:8860`**（见 `.streamlit/config.toml`）。

### Windows：`python` 不是内部或外部命令

若 PowerShell 提示找不到 `python`，说明安装时未勾选「Add Python to PATH」。可任选其一：

- 使用 **Python Launcher**：`py -m venv .venv`、`py -m pip install -r requirements.txt`、`py -m streamlit run app.py`
- 或在「应用执行别名」中关闭 `python.exe` / `python3.exe` 的商店重定向（设置 → 应用 → 应用执行别名）

### 生成设计文档（Word）

需已安装依赖（含 `python-docx`）。在项目根目录执行：

```powershell
py generate_design_doc.py
```

或双击运行 `generate_design_doc.bat`。输出：`Design/嗨Hai健康管理系统设计文档.docx`。

### Windows：提示「Port … is not available」但 netstat 里没有进程

很多机器上 **Hyper-V / WSL / Docker** 会通过系统保留一段 TCP 端口（可用下面命令查看）。常见保留区间会覆盖 **8441–8640**，因此 **8501、8510、8520、8601** 等会**无法绑定**，这不是被别的软件占用。

```powershell
netsh interface ipv4 show excludedportrange protocol=tcp
```

**处理：** 使用保留区间之外的端口（例如 **8860**、**8888**、**9000**，或 8641–49999 内任选），例如：

```powershell
streamlit run app.py --server.port 8860
```

若 **8860** 仍失败，可再换 `9005`、`14000` 等。

### 若端口确被其它程序占用

关掉其它 Streamlit 终端或结束对应 `python` 进程后重试。

### 首次运行问邮箱（Email）

可直接 **回车留空**，不必填写。若希望减少统计相关提示，可在用户目录创建 `%USERPROFILE%\.streamlit\config.toml` 并写入：

```toml
[browser]
gatherUsageStats = false
```

界面主题与布局参考 UI/UX Pro Max 中 **Wellness / Soft UI** 方向（医疗绿、浅底、卡片化指标），见 `.streamlit/config.toml` 与 `core/ui_styles.py`。

## 数据说明

- 数据库文件 `hai_data.sqlite` 在首次运行时生成，已加入 `.gitignore`。
- 示例检验文本：`data/samples/demo_report.txt`；示例体征：`data/samples/vitals_demo.csv`。
- RAG 知识片段：`data/knowledge/*.md`。

详细设计见 `Design/Design.md`。

## 推送到 GitHub 与队友协作

本目录已是**独立 Git 仓库**（勿在用户主目录执行 `git add`，应在 `MedAi` 根目录操作）。

1. 在 GitHub 新建空仓库（不要勾选「自动添加 README」，避免首次推送冲突）。  
2. 本地执行（将 URL 换成你的仓库；主分支为 **`main`**）：

```powershell
cd C:\Users\Xile\.vscode\.code\MedAi
git remote add origin https://github.com/你的用户名/仓库名.git
git push -u origin main
```

若 GitHub 创建仓库时自动生成了 `main`（仅含 README），首次推送可能被拒绝，可先执行  
`git pull origin main --rebase --allow-unrelated-histories` 再 `git push -u origin main`，或在确认无重要远程内容后使用  
`git push -u origin main --force-with-lease` 用本地项目覆盖远程 `main`。

3. 队友克隆后：复制 `.env.example` 为 `.env` 并自行填写 `DEEPSEEK_API_KEY`；勿将 `.env` 提交到 Git。

首次登录 GitHub 若提示认证，可使用 **Personal Access Token** 代替密码，或配置 **Git Credential Manager**。
