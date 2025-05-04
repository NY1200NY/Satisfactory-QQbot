from plugins.base_plugin import BasePlugin
from message import MessageSender
from auth_manager import auth_manager
import aiohttp
import logging
import configparser
import os
import platform

class FactoryPlugin(BasePlugin):
    """
    Factory专用服务器管理插件
    命令：Factory [子命令]
    """
    
    def __init__(self):
        super().__init__(
            command="Factory",
            description="管理Satisfactory专用服务器",
            is_builtin=False,
            hidden=False
        )
        self.logger = logging.getLogger("plugin.Factory")
        self.config_path = os.path.join(os.path.expanduser("~"), ".satisfactory-bot.ini")
        self.server_url = None
        self.load_config()

    def load_config(self):
        """加载服务器配置"""
        self.config = configparser.ConfigParser()
        self.config.read(self.config_path)
        
        if not self.config.has_section("server"):
            self.config.add_section("server")
        
        self.server_url = self.config.get("server", "url", fallback=None)
        self.token = self.config.get("server", "token", fallback=None)

    async def save_config(self):
        """保存配置到文件"""
        with open(self.config_path, "w") as f:
            self.config.write(f)

    async def send_command(self, func_name, data=None):
        """异步发送命令到服务器"""
        try:
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.server_url}/api/v1",
                    json={"function": func_name, "data": data or {}},
                    headers=headers,
                    ssl=False
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        self.logger.error(f"请求失败: {response.status}")
                        return None
        except Exception as e:
            self.logger.error(f"网络请求异常: {str(e)}")
            return None

    async def handle(self, params: str, user_id: str = None, **kwargs) -> str:
        """处理命令入口"""
        if not params.strip():
            return "❌ 请输入子命令，可用命令：status/save/shutdown/sessions/options/setup"
        
        if not await self.check_permissions(user_id):
            return "❌ 权限不足，需要管理员权限"

        parts = params.strip().split(maxsplit=2)
        subcommand = parts[0].lower() if parts else ""
        args = parts[1:] if len(parts) > 1 else []

        handlers = {
            "status": self.handle_status,
            "save": self.handle_save,
            "shutdown": self.handle_shutdown,
            "sessions": self.handle_sessions,
            "options": self.handle_options,
            "setup": self.handle_setup
        }

        if subcommand in handlers:
            return await handlers[subcommand](*args, user_id=user_id)
        return "❌ 未知命令，可用子命令：status/save/shutdown/sessions/options/setup"

    async def check_permissions(self, user_id):
        """检查管理员权限"""
        return auth_manager.is_admin(user_id)

    async def handle_setup(self, *args, user_id):
        """初始化服务器配置"""
        if len(args) < 2:
            return "❌ 参数不足，格式：setup [服务器地址:端口] [密码]"
        
        host, password = args[0], args[1]
        self.server_url = f"https://{host}"
        self.config["server"]["url"] = self.server_url
        
        # 获取新token
        auth_data = {"Password": password, "MinimumPrivilegeLevel": "Administrator"}
        response = await self.send_command("PasswordLogin", auth_data)
        if response and response.get("data"):
            self.token = response["data"].get("authenticationToken")
            self.config["server"]["token"] = self.token
            await self.save_config()
            return "✅ 服务器配置成功"
        return "❌ 认证失败，请检查密码"

    async def handle_status(self, *args, user_id):
        """获取服务器状态"""
        response = await self.send_command("QueryServerState")
        if not response:
            return "❌ 无法获取服务器状态"
        
        state = response.get("data", {}).get("serverGameState", {})
        if not state:
            return "❌ 服务器状态数据异常"
        
        msg = [
            "🖥️ 服务器状态",
            f"运行状态: {'✅ 运行中' if state.get('isGameRunning') else '❌ 已停止'}",
            f"玩家: {state.get('numConnectedPlayers', 0)}/{state.get('playerLimit', '?')}",
            f"存档: {state.get('activeSessionName', '无')}",
            f"运行时间: {self.format_duration(state.get('totalGameDuration', 0))}",
            f"Tick率: {state.get('averageTickRate', '?')} FPS"
        ]
        return "\n".join(msg)

    async def handle_save(self, *args, user_id):
        """保存游戏"""
        if not args:
            return "❌ 需要指定存档名称"
        
        save_name = args[0]
        response = await self.send_command("SaveGame", {"SaveName": save_name})
        if response and response.get("returnCode") == 0:
            return f"✅ 存档 {save_name} 保存成功"
        return "❌ 存档保存失败"

    async def handle_shutdown(self, *args, user_id):
        """关闭服务器"""
        response = await self.send_command("Shutdown")
        if response and response.get("returnCode") == 0:
            return "✅ 服务器关闭指令已发送"
        return "❌ 关闭指令发送失败"

    async def handle_sessions(self, *args, user_id):
        """列出服务器会话"""
        try:
            response = await self.send_command("EnumerateSessions")
            if not response:
                return "❌ 无法获取会话列表"
            
            sessions = response.get("data", {}).get("sessions", [])
            current_idx = response.get("data", {}).get("currentSessionIndex", -1)
            
            if not sessions:
                return "❌ 未找到有效会话"
            
            msg = ["📂 服务器会话列表"]
            for idx, session in enumerate(sessions):
                session_name = session.get("sessionName", "未命名会话")
                saves = session.get("saveHeaders", [])
                
                # 添加会话状态标记
                status_flag = "✅" if idx == current_idx else "⏸️"
                msg.append(f"\n{status_flag} 会话 {idx+1}: {session_name}")
                
                # 添加存档信息
                if saves:
                    for save_idx, save in enumerate(saves, 1):
                        play_time = self.format_duration(save.get("playDurationSeconds", 0))
                        msg.append(f"   💾 存档{save_idx}: {save.get('saveName')}")
                        msg.append(f"      ⏱️ 游戏时间: {play_time}")
                        msg.append(f"      🗺️ 地图: {save.get('mapName')}")
                else:
                    msg.append("   🚫 无存档")
            
            return "\n".join(msg)
        except KeyError as e:
            self.logger.error(f"数据解析失败: {str(e)}")
            return "❌ 服务器返回数据格式异常"
        except Exception as e:
            self.logger.error(f"处理会话列表时出错: {str(e)}")
            return "❌ 获取会话列表时发生意外错误"

    async def handle_options(self, *args, user_id):
        """获取服务器配置"""
        try:
            response = await self.send_command("GetServerOptions")
            if not response:
                return "❌ 无法获取服务器配置"
            
            options = response.get("data", {}).get("serverOptions", {})
            if not options:
                return "❌ 未找到有效配置"
            
            msg = ["⚙️ 服务器配置"]
            for key, value in options.items():
                msg.append(f"{key}: {value}")
            return "\n".join(msg)
        except Exception as e:
            self.logger.error(f"获取配置时出错: {str(e)}")
            return "❌ 获取服务器配置时发生错误"

    def format_duration(self, seconds):
        """格式化时间"""
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours}小时{minutes}分{seconds}秒"

# 注册插件
def register_plugin():
    return FactoryPlugin()