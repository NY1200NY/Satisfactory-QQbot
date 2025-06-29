from plugins.base_plugin import BasePlugin
from auth_manager import auth_manager
import aiohttp
import logging
import configparser
import os
import re
import asyncio
from io import StringIO
from typing import Optional, Dict, Any

class FactoryPlugin(BasePlugin):
    """
    SatisFactory专用服务器管理插件
    支持用户绑定个人服务器
    命令: Factory [子命令]
    """
    
    def __init__(self):
        super().__init__(
            command="Factory",
            description="管理Satisfactory专用服务器（支持个人绑定）",
            is_builtin=False,
            hidden=False
        )
        self.logger = logging.getLogger("plugin.Factory")  # 内部日志保持点格式
        self.config_path = os.path.join(os.path.expanduser("~"), ".Factory-bot.ini")  # 配置文件保持点格式
        self.config = self.load_config()

    def format_display_url(self, url: str) -> str:
        """将URL中的点转换为逗号（仅用于显示）"""
        return url.replace(".", ",") if url else url

    def load_config(self) -> configparser.ConfigParser:
        """加载服务器配置（内部保持点格式）"""
        config = configparser.ConfigParser()
        if os.path.exists(self.config_path):
            config.read(self.config_path)
        
        if not config.has_section("users"):
            config.add_section("users")
        return config

    async def save_config(self):
        """保存配置到文件（内部保持点格式）"""
        with open(self.config_path, "w") as f:
            self.config.write(f)

    def get_user_config(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户配置（内部保持点格式）"""
        user_key = f"user_{user_id}"
        if not self.config.has_section(user_key):
            return None
        
        return {
            "server_url": self.config.get(user_key, "server_url", fallback=None),
            "token": self.config.get(user_key, "token", fallback=None),
            "server_name": self.config.get(user_key, "server_name", fallback="未命名服务器")
        }

    async def set_user_config(self, user_id: str, server_url: str, token: str, server_name: str) -> bool:
        """设置用户配置（内部保持点格式）"""
        user_key = f"user_{user_id}"
        if not self.config.has_section(user_key):
            self.config.add_section(user_key)
        
        self.config.set(user_key, "server_url", server_url)
        self.config.set(user_key, "token", token)
        self.config.set(user_key, "server_name", server_name)
        
        await self.save_config()
        return True

    async def send_command(self, server_url: str, token: Optional[str], func_name: str, data: Optional[Dict] = None) -> Optional[Dict]:
        """异步发送命令到服务器（内部使用标准点格式）"""
        try:
            headers = {"Authorization": f"Bearer {token}"} if token else {}
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{server_url}/api/v1",
                    json={"function": func_name, "data": data or {}},
                    headers=headers,
                    ssl=False,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    self.logger.error(f"请求失败: {response.status} {await response.text()}")
        except Exception as e:
            self.logger.error(f"网络请求异常: {str(e)}")
        return None

    async def handle(self, params: str, user_id: str = None, **kwargs) -> str:
        """处理命令入口"""
        if not params.strip():
            return await self.show_help()
        
        parts = params.strip().split(maxsplit=1)
        subcommand = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        handlers = {
            "status": self.handle_status,
            "save": self.handle_save,
            "shutdown": self.handle_shutdown,
            "sessions": self.handle_sessions,
            "options": self.handle_options,
            "bind": self.handle_bind,
            "unbind": self.handle_unbind,
            "info": self.handle_info,
            "help": self.show_help
        }

        handler = handlers.get(subcommand)
        return await handler(user_id, args) if handler else "❌ 未知命令，输入 /Factory help 查看帮助"

    async def show_help(self, user_id=None, args=None) -> str:
        """显示帮助信息（消息中使用逗号格式）"""
        return (
            "🛠️ Satisfactory 服务器管理帮助:\n"
            "--------------------------------\n"
            "1. 绑定服务器: /Factory bind [名称] [地址:端口] [密码]\n"
            "  示例: /Factory bind 主服务器 example,com:7777 mypassword\n\n"
            "2. 查看绑定信息: /Factory info\n\n"
            "3. 解除绑定: /Factory unbind\n\n"
            "4. 服务器状态: /Factory status\n\n"
            "5. 保存游戏: /Factory save [存档名]\n\n"
            "6. 关闭服务器: /Factory shutdown confirm\n\n"
            "7. 会话列表: /Factory sessions\n\n"
            "8. 服务器配置: /Factory options\n\n"
            "9. 帮助: /Factory help"
        )

    async def handle_bind(self, user_id: str, args: str) -> str:
        """绑定个人服务器（用户输入可使用任意格式）"""
        if not args:
            return "❌ 参数不足，格式：bind [名称] [地址:端口] [密码]"
        
        # 允许用户输入点或逗号格式
        args = args.replace(",", ".")  # 统一转换为点格式处理
        
        match = re.match(r'^(\S+)\s+([\w.-]+)(?::(\d+))?\s+(\S+)$', args)
        if not match:
            return "❌ 参数格式错误，正确格式：bind [名称] [地址] [密码] (端口可选，默认7777)"
        
        server_name, server_host, server_port, password = match.groups()
        server_port = server_port or "7777"
        server_url = f"https://{server_host}:{server_port}"
        
        response = await self.send_command(server_url, None, "PasswordLogin", {
            "Password": password,
            "MinimumPrivilegeLevel": "Administrator"
        })
        
        if not response:
            return "❌ 无法连接到服务器，请检查地址和端口"
        if response.get("error"):
            return f"❌ 连接错误: {response['error']}"
        if not (response.get("data") and response["data"].get("authenticationToken")):
            return f"❌ 认证失败: {response.get('message', '请检查密码')}"
        
        await self.set_user_config(user_id, server_url, response["data"]["authenticationToken"], server_name)
        display_url = self.format_display_url(f"{server_host}:{server_port}")
        return f"✅ 成功绑定服务器: {server_name} ({display_url})"

    async def handle_info(self, user_id: str, args: str) -> str:
        """查看绑定信息（显示消息时转换格式）"""
        user_config = self.get_user_config(user_id)
        if not user_config:
            return "❌ 您尚未绑定任何服务器，使用 /Factory bind 绑定"
        
        display_url = self.format_display_url(user_config["server_url"][8:] if user_config["server_url"] else "未知")
        hidden_token = user_config['token'][:4] + '****' + user_config['token'][-4:] if user_config['token'] else "未设置"
        
        return (
            f"🔒 您的服务器绑定信息:\n"
            f"名称: {user_config['server_name']}\n"
            f"地址: {display_url}\n"
            f"令牌: {hidden_token}"
        )

    async def handle_status(self, user_id: str, args: str) -> str:
        """获取服务器状态（显示消息时转换格式）"""
        user_config = self.get_user_config(user_id)
        if not user_config:
            return "❌ 请先绑定服务器：/Factory bind [名称] [地址] [密码]"
        
        response = await self.send_command(user_config["server_url"], user_config["token"], "QueryServerState")
        if not response:
            return f"❌ 无法连接到服务器: {user_config['server_name']}"
        
        state = response.get("data", {}).get("serverGameState", {})
        if not state:
            return "❌ 服务器状态数据异常"
        
        display_url = self.format_display_url(user_config["server_url"][8:]) if user_config["server_url"] else "未知"
        
        return (
            f"🖥️ 服务器状态 ({user_config['server_name']})\n"
            f"地址: {display_url}\n"
            f"状态: {'✅ 运行中' if state.get('isGameRunning') else '❌ 已停止'}\n"
            f"玩家: {state.get('numConnectedPlayers', 0)}/{state.get('playerLimit', '?')}\n"
            f"运行时间: {self.format_duration(state.get('totalGameDuration', 0))}"
        )

    def format_duration(self, seconds: int) -> str:
        """格式化时间"""
        hours, remainder = divmod(int(seconds), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours}小时{minutes}分{seconds}秒"

    async def handle_save(self, user_id: str, args: str) -> str:
        """保存游戏"""
        if not args.strip():
            return "❌ 需要指定存档名称"
        
        user_config = self.get_user_config(user_id)
        if not user_config:
            return "❌ 请先绑定服务器"
        
        response = await self.send_command(
            user_config["server_url"],
            user_config["token"],
            "SaveGame",
            {"SaveName": args.strip()}
        )
        return f"✅ 存档 {args.strip()} 保存成功" if response and response.get("returnCode") == 0 else "❌ 保存失败"

    async def handle_shutdown(self, user_id: str, args: str) -> str:
        """关闭服务器"""
        if args.strip().lower() != "confirm":
            return "⚠️ 请确认关闭: /Factory shutdown confirm"
        
        user_config = self.get_user_config(user_id)
        if not user_config:
            return "❌ 请先绑定服务器"
        
        response = await self.send_command(
            user_config["server_url"],
            user_config["token"],
            "Shutdown"
        )
        return "✅ 关闭指令已发送" if response and response.get("returnCode") == 0 else "❌ 关闭失败"

    async def handle_sessions(self, user_id: str, args: str) -> str:
        """列出会话（优化版：只显示3个最新存档，完整发送）"""
        user_config = self.get_user_config(user_id)
        if not user_config:
            return "❌ 请先绑定服务器：/Factory bind [名称] [地址] [密码]"

        # 获取会话数据
        response = await self.send_command(
            user_config["server_url"],
            user_config["token"],
            "EnumerateSessions"
        )
        if not response:
            return f"❌ 无法获取会话列表：{user_config['server_name']}"

        sessions = response.get("data", {}).get("sessions", [])
        if not sessions:
            return "❌ 该服务器没有可用会话"

        # 构建完整消息
        display_url = self.format_display_url(user_config["server_url"][8:])
        msg = [
            f"📂 服务器会话列表 ({user_config['server_name']})",
            f"地址: {display_url}",
            f"当前会话: {len(sessions)}个"
        ]

        for session_idx, session in enumerate(sessions[:3]):  # 限制最多3个会话
            session_name = session.get("sessionName", "未命名会话")
            saves = session.get("saveHeaders", [])
            
            msg.append(f"\n🔷 会话 {session_idx+1}: {session_name}")
            
            if saves:
                # 按保存时间排序（假设saveHeaders中有saveDateTime字段）
                sorted_saves = sorted(
                    saves,
                    key=lambda x: x.get("saveDateTime", ""),
                    reverse=True
                )[:3]  # 每个会话最多显示3个存档
                
                for save_idx, save in enumerate(sorted_saves, 1):
                    save_time = save.get("saveDateTime", "未知时间")
                    play_time = self.format_duration(save.get("playDurationSeconds", 0))
                    msg.extend([
                        f"   💾 存档{save_idx}: {save.get('saveName', '未知存档')}",
                        f"      🕒 保存时间: {save_time}",
                        f"      ⏱️ 游戏时间: {play_time}",
                        f"      🗺️ 地图: {save.get('mapName', '未知地图')}",
                        f"      🏷️ 版本: {save.get('buildVersion', '未知')}"
                    ])
            else:
                msg.append("   🚫 无存档数据")

        # 添加提示信息
        if len(sessions) > 3:
            msg.append(f"\n⚠️ 只显示前3个会话（共{len(sessions)}个）")

        return "\n".join(msg)

    async def handle_options(self, user_id: str, args: str) -> str:
        """获取配置"""
        user_config = self.get_user_config(user_id)
        if not user_config:
            return "❌ 请先绑定服务器"
        
        response = await self.send_command(
            user_config["server_url"],
            user_config["token"],
            "GetServerOptions"
        )
        if not response:
            return "❌ 获取配置失败"
        
        options = response.get("data", {}).get("serverOptions", {})
        return "\n".join([f"{k}: {v}" for k, v in options.items()]) if options else "❌ 无配置数据"

    async def handle_unbind(self, user_id: str, args: str) -> str:
        """解除绑定"""
        if await self.remove_user_config(user_id):
            return "✅ 已解除绑定"
        return "❌ 您尚未绑定服务器"

    async def remove_user_config(self, user_id: str) -> bool:
        """移除用户配置"""
        user_key = f"user_{user_id}"
        if self.config.has_section(user_key):
            self.config.remove_section(user_key)
            await self.save_config()
            return True
        return False

# 注册插件
def register_plugin():
    return FactoryPlugin()
