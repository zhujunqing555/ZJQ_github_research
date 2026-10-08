# ZJQ_github_research

为科研工作发现值得使用的 GitHub 项目：结合个人科研画像、真实实现与近7天关注变化，推荐科研辅助、科研短视频及微信公众号工具。

显示名为 **ZJQ_github_research**，Codex 调用标识为 **`$zjq-github-research`**。技能入口位于 [`skills/zjq-github-research/SKILL.md`](skills/zjq-github-research/SKILL.md)。

## 能做什么

| 方向 | 默认检索投入 | 关注能力 |
|---|---:|---|
| 科研辅助 | 60% | 文献/PDF与证据核验、单细胞/多组学、数据分析、代码复现、学术写作、AI蛋白设计、机器学习学习 |
| 科研短视频 | 15% | 脚本、分镜、图解动画、中文配音、专业字幕、音画同步、剪辑与竖屏导出 |
| 微信公众号 | 15% | 文献推文、标题摘要、排版、封面、图片上传及草稿辅助 |
| 核验与补漏 | 10% | 原始仓库核验、依赖检查、跨方向补漏 |

每天最多3个重点项目，质量不足允许0条。首次启用的30天可发现不限发布时间的成熟项目；之后优先近7天热度或实质升级。质量分与Stars分开，不用累计Stars冒充周增长。仓库重命名、子skill和用户反馈分别记录，避免重复推荐。

## 安装到Codex

让Codex从[本仓库的技能目录](https://github.com/zhujunqing555/ZJQ_github_research/tree/main/skills/zjq-github-research)安装 `skills/zjq-github-research`，或将该目录复制到 `$CODEX_HOME/skills/zjq-github-research`。未设置 `CODEX_HOME` 时，通常使用用户主目录下的 `.codex`。

安装后可以直接说：

> 使用 $zjq-github-research，读取我的科研画像，完成今天的GitHub科研项目雷达。

首次运行会初始化本地状态。科研画像读取项目 `USER.md`，不存在则使用 `$CODEX_HOME/USER.md`；缺少画像时按明确给出的研究任务或默认模板执行，不凭空编造个人资料。

也可以手动初始化（Python3.9及以上）：

```sh
python skills/zjq-github-research/scripts/init_radar.py --timezone Asia/Shanghai
```

该命令只创建缺失文件，保留既有配置、候选、反馈和自动化ID。`--date YYYY-MM-DD` 可指定首次启用日期；`--state-dir PATH` 可指定状态目录。日常默认状态位于 `$CODEX_HOME/skill-radars/zjq-github-research`，与分发源码分开保存。

## 定时推送

安装技能本身不会建立定时任务。你可以明确要求Codex：

> 为ZJQ_github_research建立每天北京时间08:00的推送，在当前聊天运行。周日整合周榜，无有效新发现时保持安静。

Codex将使用应用支持的自动化工具建立或更新任务；本地定时运行需要电脑与Codex可用。候选只有在你明确选中后才安装；公众号账户接入、素材上传和正式发布分别处理。

## 只读采集与验证

采集助手仅使用Python标准库，支持公开仓库搜索、元数据、Stars历史、本地快照与技能入口清单。网络请求失败会记录原因；没有7天基线时热度未知。可选使用运行环境已有的 `GITHUB_TOKEN` / `GH_TOKEN`，密钥不写入仓库或报告。

```sh
python skills/zjq-github-research/scripts/github_radar.py --help
python skills/zjq-github-research/scripts/test_github_radar.py
python skills/zjq-github-research/scripts/test_init_radar.py
```

助手结果需要继续核验原作者资料、真实入口、许可证、环境与示例，静态阅读不能写成已试跑。`USER.md`、凭据、个人运行数据、推送历史和本机定时配置不属于本仓库的分发内容。
