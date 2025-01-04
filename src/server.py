import asyncio
import logging
import os
import time
import hmac
import base64
import hashlib
import json
from typing import List
from urllib.parse import quote_plus

import aiohttp
from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.stdio import stdio_server

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("dingding_mcp_server")

class DingdingMCPServer:
    def __init__(self):
        self.app = Server("dingding_mcp_server")
        self.setup_tools()
        self.access_token = None
        self.token_expires = 0
        self.session = None

    def get_sign(self):
        timestamp = str(round(time.time() * 1000))
        secret = os.environ.get("DINGTALK_APP_SECRET")
        secret_enc = secret.encode('utf-8')
        string_to_sign = '{}\n{}'.format(timestamp, secret)
        string_to_sign_enc = string_to_sign.encode('utf-8')
        hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
        sign = quote_plus(base64.b64encode(hmac_code))
        return timestamp, sign

    async def ensure_session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()

    async def get_access_token(self):
        if self.access_token and time.time() < self.token_expires:
            return self.access_token

        await self.ensure_session()
        app_key = os.environ.get("DINGTALK_APP_KEY")
        app_secret = os.environ.get("DINGTALK_APP_SECRET")

        if not all([app_key, app_secret]):
            raise ValueError("Missing DingTalk API credentials in environment variables")

        url = "https://oapi.dingtalk.com/gettoken"
        params = {
            "appkey": app_key,
            "appsecret": app_secret
        }

        async with self.session.get(url, params=params) as response:
            data = await response.json()
            if data.get("errcode") == 0:
                self.access_token = data["access_token"]
                self.token_expires = time.time() + data["expires_in"] - 200  # 提前200秒更新
                return self.access_token
            else:
                raise Exception(f"Failed to get access token: {data}")

    def setup_tools(self):
        @self.app.list_tools()
        async def list_tools() -> List[Tool]:
            return [
                Tool(
                    name="send_message",
                    description="Send a message to a DingTalk conversation",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "conversation_id": {
                                "type": "string",
                                "description": "ID of the DingTalk conversation"
                            },
                            "message": {
                                "type": "string",
                                "description": "Message content to send"
                            },
                            "msg_type": {
                                "type": "string",
                                "description": "Message type (text/markdown/link/etc)",
                                "default": "text"
                            }
                        },
                        "required": ["conversation_id", "message"]
                    }
                ),
                Tool(
                    name="get_conversation_info",
                    description="Get information about a DingTalk conversation",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "conversation_id": {
                                "type": "string",
                                "description": "ID of the DingTalk conversation"
                            }
                        },
                        "required": ["conversation_id"]
                    }
                ),
                Tool(
                    name="get_user_info",
                    description="Get information about a DingTalk user",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "user_id": {
                                "type": "string",
                                "description": "ID of the DingTalk user"
                            }
                        },
                        "required": ["user_id"]
                    }
                )
            ]

        @self.app.call_tool()
        async def call_tool(name: str, arguments: dict) -> List[TextContent]:
            await self.ensure_session()
            access_token = await self.get_access_token()
            
            if name == "send_message":
                conversation_id = arguments["conversation_id"]
                message = arguments["message"]
                msg_type = arguments.get("msg_type", "text")
                
                try:
                    url = "https://oapi.dingtalk.com/message/send_to_conversation"
                    params = {"access_token": access_token}
                    
                    if msg_type == "text":
                        msg_content = {"content": message}
                    elif msg_type == "markdown":
                        msg_content = {
                            "title": "消息",
                            "text": message
                        }
                    else:
                        return [TextContent(type="text", text=f"Unsupported message type: {msg_type}")]

                    data = {
                        "receiver": conversation_id,
                        "msg": {
                            "msgtype": msg_type,
                            msg_type: msg_content
                        }
                    }

                    async with self.session.post(url, params=params, json=data) as response:
                        result = await response.json()
                        if result.get("errcode") == 0:
                            return [TextContent(type="text", text="Message sent successfully")]
                        else:
                            return [TextContent(type="text", text=f"Failed to send message: {result}")]
                except Exception as e:
                    return [TextContent(type="text", text=f"Error sending message: {str(e)}")]
            
            elif name == "get_conversation_info":
                conversation_id = arguments["conversation_id"]
                
                try:
                    url = "https://oapi.dingtalk.com/chat/get"
                    params = {
                        "access_token": access_token,
                        "chatid": conversation_id
                    }

                    async with self.session.get(url, params=params) as response:
                        result = await response.json()
                        if result.get("errcode") == 0:
                            return [TextContent(type="text", text=f"Conversation info: {json.dumps(result, ensure_ascii=False)}")]
                        else:
                            return [TextContent(type="text", text=f"Failed to get conversation info: {result}")]
                except Exception as e:
                    return [TextContent(type="text", text=f"Error getting conversation info: {str(e)}")]
            
            elif name == "get_user_info":
                user_id = arguments["user_id"]
                
                try:
                    url = "https://oapi.dingtalk.com/user/get"
                    params = {
                        "access_token": access_token,
                        "userid": user_id
                    }

                    async with self.session.get(url, params=params) as response:
                        result = await response.json()
                        if result.get("errcode") == 0:
                            return [TextContent(type="text", text=f"User info: {json.dumps(result, ensure_ascii=False)}")]
                        else:
                            return [TextContent(type="text", text=f"Failed to get user info: {result}")]
                except Exception as e:
                    return [TextContent(type="text", text=f"Error getting user info: {str(e)}")]
            
            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]

    async def run(self):
        logger.info("Starting DingTalk MCP server...")
        
        async with stdio_server() as (read_stream, write_stream):
            try:
                await self.app.run(
                    read_stream,
                    write_stream,
                    self.app.create_initialization_options()
                )
            except Exception as e:
                logger.error(f"Server error: {str(e)}", exc_info=True)
                raise
            finally:
                if self.session:
                    await self.session.close()

def main():
    server = DingdingMCPServer()
    asyncio.run(server.run())

if __name__ == "__main__":
    main() 