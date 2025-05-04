# 这是什么?
这是基于开朗的火山河123开发的[hiklqqbot](https://github.com/kldhsh123/hiklqqbot)开发的社区插件.
>我们鼓励您使用hiklqqbot项目进行开发官方机器人插件
## 如何安装?
首先,你需要懂得如何使用hiklqqbot官方机器人项目 (
1. 下载本项目[releases](https://github.com/NY1200NY/Satisfactory-QQbot/releases/)中的Satisfactory.py脚本
2. 放入hiklqqbot程序中的plugins目录中
3. 安装成功，开始使用吧~
### 如何使用?
1. 在您的群聊中发送/Factory指令
您应该会看到
```
❌ 请输入子命令，可用命令：status/save/shutdown/sessions/options/setup
```
### 那么如何使用这些子命令呢?
- 发送 /Factory status 会返回:
```
Satisfactory
🖥️ 服务器状态
运行状态: ✅ 运行中
玩家: 0/100
存档: xxx
运行时间: x小时x分x秒
Tick率: 30.0 TPS
版本: CL#385279(Version1.0)
```
- 发送 /Factory save 会返回:
```
✅ 存档 xxx 保存成功
```
- 发送 /Factory shutdown 会返回:
```
✅ 服务器关闭指令已发送
```
- 发送 /Factory sessions 会返回:
```
📂 服务器会话列表

✅ 会话 1: xxx服务器
   💾 存档1: xxx
      ⏱️ 游戏时间: xx小时x分x秒
      🗺️ 地图: Persistent_Level
```
- 发送 /Factory options 会返回:
```
⚙️ 服务器配置
FG.DSAutoPause: False
FG.DSAutoSaveOnDisconnect: False
FG.DisableSeasonalEvents: False
FG.AutosaveInterval: 150.0
FG.ServerRestartTimeSlot: 300.0
FG.SendGameplayData: True
FG.NetworkQuality: 3
```
---
## 常见问题
1. 返回❌ 无法获取服务器配置
- 解决方案......

本文档尚未完工，有问题提交issues
