# 嗨 Hai（Hai）

医学人工智能课程演示项目：本地 Streamlit + SQLite + 轻量 RAG + 规则化体征预警；大模型默认 **DeepSeek API**（OpenAI 兼容），可选 [Ollama](https://ollama.com/) 作为回退。

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

## 可选：Ollama（回退）

安装 Ollama 后执行例如：

```bash
ollama pull llama3.2
```

默认连接 `http://127.0.0.1:11434`，模型名 `llama3.2`。可通过环境变量 `OLLAMA_HOST`、`OLLAMA_MODEL` 修改。

## 数据说明

- 数据库文件 `hai_data.sqlite` 在首次运行时生成，已加入 `.gitignore`。
- 示例检验文本：`data/samples/demo_report.txt`；示例体征：`data/samples/vitals_demo.csv`。
- RAG 知识片段：`data/knowledge/*.md`。

详细设计见 `Design/Design.md`。
