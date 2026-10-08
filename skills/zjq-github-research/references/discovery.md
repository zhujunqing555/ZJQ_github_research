# 项目发现与数据口径

## 可迁移的检索矩阵

对一个任务分别组合任务术语、方法/生态、输入格式与交付形式；避免将所有研究方向AND在同一个查询里。

| 子任务 | 发现词族 | 重点入口 |
|---|---|---|
| 科研PDF与引文 | scientific PDF, document parsing, table/figure extraction, citation, evidence | README、实际解析/导出示例、论文官方代码 |
| 单细胞机制 | single-cell, AnnData, Seurat, spatial, regulatory network, perturbation, cell communication | 作者仓库、教程/vignette、分析Notebook |
| CRC–T2D因果与共同靶点 | cross-trait, colocalization, fine-mapping, MR, immunometabolism, target prioritization | PubMed/论文代码链接、官方软件与公开数据示例 |
| AI蛋白与递送 | protein design, binder, antibody, peptide, developability, structure, delivery | 模型推理/评价入口、权重与许可、案例 |
| ML/DL学习 | machine learning tutorial, deep learning, PyTorch, notebook, biomedical classification, interpretable, benchmark | 可运行练习、公开数据、前置知识、评价与数据划分 |
| 科研短视频 | animation, voiceover, subtitle, captions, audio alignment, timeline, video rendering | 实际skill/渲染入口、中文样例、TTS与字幕依赖 |
| 微信公众号 | WeChat, 微信公众号, Markdown, draft, image upload, article formatting | 排版与草稿脚本、后台交付示例、API/浏览器路径 |

查询例子（仓库搜索，不是代码搜索）：

```
"single-cell" in:name,description,readme archived:false
"scientific" "PDF" in:readme archived:false
"PyTorch" "tutorial" in:readme archived:false
"wechat" "draft" in:readme archived:false
"video" "captions" in:readme archived:false
```

若结果超过搜索上限或返回不完整，按子任务、来源组织、语言/生态分片。R或Notebook多语言仓库不要只因主语言不同而排除。用已核验来源的 `org:`/`user:` 查配套；从官方示例、manifest/教程扩展一层，明确配套解决哪个实际缺口。缺少Used by不等于没有科研应用。

## 证据来源顺序

1. 原始GitHub仓库与具体入口；代码/文档的commit与许可证。
2. 作者论文、官网、模型卡、官方教程或案例。生医论文优先PubMed核对代码链接；AI方法可用作者原文/预印本与官网。当前任务不是论文IF雷达。
3. GitHub Trending周入口与topic/合集/搜索引擎用于发现，不能单独证明质量或全球热度排名。

可信种子在动态状态目录 `sources.json`；种子只是检索起点，不能因为在清单中就自动推荐全部子技能。定期增补经过实际核验的原作者/组织与教程。

## Stars采集的具体限制

- 当前官方history路径：`GET /repos/{owner}/{repo}/stargazers/history`，自然周分组，days由Sunday开始；周/日边界不能默认UTC。实现必须保留源时间边界，并将无法确认当前源日的区间标为近似/边界待核验。
- 可获取日聚合时显示“最近7个完整API日新增Stars”，记录源week timestamp、取用day indexes及完整性。没有精确小时记录时不要叫过去168小时。
- history不可用则在本地保存日期/总Stars快照；有合适7天间隔时仅报告“7天Stars净增长”及实际间隔。累计Stars可以报告，总量不能充当周增长。
- HTTP403/429、鉴权、超时、404/不支持端点都是采集状态；禁止空结果替代失败，禁止无限重试。无需获取打星用户个人列表。
- 同口径热度优先同赛道排序。没有完整数据的候选进入成熟建库或待核验项，不能冒充周热榜。

维护时核对主来源：

- [仓库搜索](https://docs.github.com/en/search-github/searching-on-github/searching-for-repositories)
- [REST搜索限制](https://docs.github.com/en/rest/search/search)
- [Stars及聚合历史](https://docs.github.com/en/rest/activity/starring)
- [聚合历史接口公告](https://github.blog/changelog/2026-09-04-new-api-endpoint-provides-privacy-safe-star-history-data/)

## 本地只读采集助手

在本技能目录调用 `scripts/github_radar.py`，只读公开接口与指定目录的 SKILL.md，不执行候选代码。`--query` 和 `--repo` 可重复，`--limit` 是每个查询的结果数上限，不代表完整排名。以下 PowerShell 示例解析 `CODEX_HOME`，未设置时退回用户主目录下的 `.codex`；有自定义状态目录时替换 `$radarState`，并保留 `--state` 指向该目录的快照文件。

```powershell
$radarCodexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME '.codex' }
$radarState = Join-Path $radarCodexHome 'skill-radars/zjq-github-research'
python -X utf8 scripts/init_radar.py --date 'YYYY-MM-DD' --timezone 'Asia/Shanghai' --state-dir $radarState
python -X utf8 scripts/github_radar.py collect --repo 'OWNER/REPO' --query '"single-cell" in:name,description,readme archived:false' --limit 10 --report-date 'YYYY-MM-DD' --state (Join-Path $radarState 'state/star_snapshots.json') --output (Join-Path $radarState 'runs/YYYY-MM-DD-collection.json')
python -X utf8 scripts/github_radar.py inventory --root (Join-Path $radarCodexHome 'skills') --output (Join-Path $radarState 'runs/YYYY-MM-DD-installed-skills.json')
```

日期占位符须替换为实际用户本地日期；首次激活的日期不要在后续每日运行中重写。快照默认存入 `CODEX_HOME/skill-radars/zjq-github-research/state/star_snapshots.json`（`CODEX_HOME` 未设时为用户主目录下的 `.codex`）；自定义状态目录需使用 `--state` 指定。程序保留实际UTC采集时刻，`--report-date` 仅标记日报日期。退出码2表示没有成功仓库元数据，仍需阅读输出错误并按正文回退检索；退出码0也可能部分失败。

`metadata.id` 在接口返回时记录为仓库ID（输出为仓库记录的 `id` 字段）。不能从名称猜ID。对于API失败、改用页面核验的候选，保存具体入口的SHA256或可确认commit，未知ID留空。inventory只覆盖指定根目录，插件技能还须结合当前会话技能列表；不声称已验证后端部署。
