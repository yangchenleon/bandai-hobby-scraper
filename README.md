# 万代官方模型资料库爬虫 (bandai-hobby-scraper)

本项目是一个工业级的自动化爬虫工具，专门用于抓取 [万代官网 (bandai-hobby.net)](https://bandai-hobby.net/) 的模型单品数据。项目内置了完善的任务队列管理、图片补全、以及智能数据合并机制。

## 1. 核心特性

*   **双阶段任务流**：
    *   **阶段一 (Discovery)**：扫描分页列表页，自动发现新机体并进入任务队列。
    *   **阶段二 (Extraction)**：深度爬取详情页（参数、正文、高清大图），支持断点续爬。
*   **工业级队列管理**：
    *   状态机管理：`pending` (待处理), `processing` (处理中), `completed` (已完成), `failed` (失败)。
    *   **自动容错**：程序启动时会自动检测并重置上次崩溃残留的 `processing` 任务，防止幽灵任务。
*   **智能存储策略**：
    *   **Smart Merge**：更新抓取时，仅覆盖非空字段，保留已有数据。
    *   **图片补全**：自动比对本地文件数量，仅下载缺失或更新的图片。
*   **反爬避让**：内置 `Tenacity` 指数退避重试、`fake-useragent` 随机轮询以及随机请求延迟。

---

## 2. 环境配置

建议使用 Python 3.10+ 环境。

### 安装依赖
```bash
/home/chen/miniconda3/envs/unibase2/bin/pip install -r requirements.txt
```

---

## 3. 使用说明

目前主程序通过修改 `main.py` 中的配置变量来控制爬取范围。

### 执行爬取
```bash
/home/chen/miniconda3/envs/unibase2/bin/python main.py
```

### 修改爬取目标
打开 `main.py`，修改以下变量：
*   `brand_code = "MG"`：目标系列代码（如 MG, RG, HG, PG 等）。
*   `batch_size = 10`：每次从队列中捞取的任务数（建议设为 10-20）。
*   `start_page`：起始页码。

---

## 4. 进度监控 (SQL)

使用 `sqlite3 database/bandai_hobby.db` 查询实时进度：

### 查看队列整体状态
```sql
SELECT status, count(*) FROM pending_queue GROUP BY status;
```

### 查看失败的任务及错误原因
```sql
SELECT product_name, error_message FROM failed_queue;
```

---

## 5. 项目结构

*   `main.py`: 程序入口，负责调度列表发现与详情提取。
*   `src/`:
    *   `queue_manager.py`: 数据库队列核心逻辑（SQLite）。
    *   `scraper.py`: 页面请求、重试机制、User-Agent 轮询。
    *   `data_extractor.py`: HTML 属性提取与清洗。
    *   `image_downloader.py`: 图片下载及完整性校验。
*   `data/`: 存放爬取结果。
    *   每个产品拥有独立文件夹，包含 `product_details.json` 和 `images/` 子目录。
*   `database/`: 存储任务状态索引。
