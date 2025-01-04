import asyncio
import logging
import os
from typing import List
from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.stdio import stdio_server
from dingtalk import DingTalk

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

    def get_dingtalk_client(self):
        # 从环境变量获取凭证
        app_key = os.environ.get("DINGTALK_APP_KEY")
        app_secret = os.environ.get("DINGTALK_APP_SECRET")
        
        if not all([app_key, app_secret]):
            raise ValueError("Missing DingTalk API credentials in environment variables")
        
        return DingTalk(app_key, app_secret)

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
            dingtalk = self.get_dingtalk_client()
            
            if name == "send_message":
                conversation_id = arguments["conversation_id"]
                message = arguments["message"]
                msg_type = arguments.get("msg_type", "text")
                
                try:
                    response = dingtalk.send_message(
                        conversation_id=conversation_id,
                        msg_type=msg_type,
                        content={"content": message} if msg_type == "text" else message
                    )
                    return [TextContent(type="text", text=f"Message sent successfully: {response}")]
                except Exception as e:
                    return [TextContent(type="text", text=f"Error sending message: {str(e)}")]
            
            elif name == "get_conversation_info":
                conversation_id = arguments["conversation_id"]
                
                try:
                    info = dingtalk.get_chat_info(conversation_id)
                    return [TextContent(type="text", text=f"Conversation info: {info}")]
                except Exception as e:
                    return [TextContent(type="text", text=f"Error getting conversation info: {str(e)}")]
            
            elif name == "get_user_info":
                user_id = arguments["user_id"]
                
                try:
                    info = dingtalk.get_user_info(user_id)
                    return [TextContent(type="text", text=f"User info: {info}")]
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

def main():
    server = DingdingMCPServer()
    asyncio.run(server.run())

if __name__ == "__main__":
    main() 