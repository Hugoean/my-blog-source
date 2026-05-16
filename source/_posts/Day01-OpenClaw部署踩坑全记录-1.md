---
title: Day01-OpenClaw部署踩坑全记录
date: 2026-04-04
tags: [AgentAnatomy, OpenClaw, 体验]
---

**TL;DR**：Windows 上装 OpenClaw 不难，但每一步都有坑。配置不是命令行参数，是交互式向导。Web 工具默认没开，模型会静默降级到训练数据假装联网。

## 为什么写这篇

AgentAnatomy 连载第一天。先把 OpenClaw 跑起来，有第一手感受再读源码——空谈架构没意思。

## 部署过程

环境：Windows 10，Node 24.14，Git Bash。

安装没问题：
```bash
npm install -g openclaw@latest
```

8 分钟，481 个包。第一个坑：配置 API key。文档写的是：
```bash
openclaw config set api-key YOUR_KEY
```

实际报错 `value/json mode requires <value>`。正确做法是跑 `openclaw config` 进交互式向导，选 Model → DeepSeek，在里面填 key。命令行那条根本不对。

配完启动 Gateway：
```bash
openclaw gateway start
```

又报错：`Gateway service missing`，要先跑 `openclaw gateway install`。装完再 start，起来了，但日志有一条 `model-pricing bootstrap failed: TimeoutError`，pricing 服务超时。不影响用，但留着心里有点不踏实。

浏览器打开 `127.0.0.1:18791` 显示 Unauthorized。找了半天才发现要跑：
```bash
openclaw dashboard
```

它自动带 token 打开。这条命令在 `openclaw --help` 里才看得到，文档没有重点提。

## 实际使用

让它在 Workspace 创建一个 txt 文件，秒完成，文件操作没问题。

然后让它搜今天的 AI 新闻。它调用了 `web_fetch`，但返回的是"截至2024年"的内容。原因：配置时 Web tools 那步跳过了，默认没启用，fetch 失败后模型静默降级到训练数据，用户完全感知不到。这个设计有点问题，失败就应该明确报错。

## Workspace 的文件

`E:\openclaw-workspace` 里自动生成了：AGENTS.md、SOUL.md、USER.md、TOOLS.md、IDENTITY.md。这是 Agent 的行为和记忆定义，后面会细读，今天先记住它们在这。

## 和 SAGE-Code 的关联

OpenClaw 把 Agent 状态外化成文件，而不是藏在内存里。文件可读、可版本控制、可手动干预。SAGE-Code 的记忆设计可以借鉴这个思路。

## 我的判断

Windows 体验比预期粗糙：报错不友好，命令和文档有出入，Web 工具失败不报错只静默降级。但核心的文件操作和 Gateway 架构跑通了，值得继续读源码。

别对 Windows 上的 OpenClaw 体验抱太高期望。

## 参考

- [OpenClaw GitHub](https://github.com/openclaw/openclaw)
- [OpenClaw 文档](https://docs.openclaw.ai)
- [知乎完整教程](https://zhuanlan.zhihu.com/p/2012169208067282681)