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
from datetime import datetime, timedelta

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

    async def get_department_list(self, access_token: str):
        """获取部门列表"""
        url = "https://oapi.dingtalk.com/department/list"
        params = {"access_token": access_token}
        
        async with self.session.get(url, params=params) as response:
            data = await response.json()
            if data.get("errcode") == 0:
                return data["department"]
            else:
                raise Exception(f"Failed to get department list: {data}")

    async def get_department_users(self, access_token: str, department_id: int):
        """获取部门用户基础信息"""
        url = "https://oapi.dingtalk.com/user/simplelist"
        params = {
            "access_token": access_token,
            "department_id": department_id
        }
        
        async with self.session.get(url, params=params) as response:
            data = await response.json()
            if data.get("errcode") == 0:
                return data["userlist"]
            else:
                raise Exception(f"Failed to get department users: {data}")

    async def get_user_detail(self, access_token: str, userid: str):
        """获取用户详细信息"""
        url = "https://oapi.dingtalk.com/user/get"
        params = {
            "access_token": access_token,
            "userid": userid
        }
        
        async with self.session.get(url, params=params) as response:
            data = await response.json()
            if data.get("errcode") == 0:
                return data
            else:
                raise Exception(f"Failed to get user detail: {data}")

    async def get_calendar_list(self, access_token: str, userid: str, start_time: int = None, end_time: int = None, max_results: int = 50):
        """获取用户日程列表"""
        url = "https://api.dingtalk.com/v1.0/calendar/users/" + userid + "/calendars/primary/events/list"
        
        # 如果没有指定时间范围，默认查询从现在开始7天内的日程
        if not start_time:
            start_time = int(time.time() * 1000)
        if not end_time:
            end_time = int((time.time() + 7 * 24 * 3600) * 1000)  # 默认7天
        
        headers = {
            "x-acs-dingtalk-access-token": access_token,
            "Content-Type": "application/json"
        }
        
        data = {
            "maxResults": max_results,
            "timeMin": start_time,
            "timeMax": end_time
        }
        
        async with self.session.post(url, headers=headers, json=data) as response:
            result = await response.json()
            if "items" in result:
                return result
            else:
                raise Exception(f"Failed to get calendar list: {result}")

    def setup_tools(self):
        @self.app.list_tools()
        async def list_tools() -> List[Tool]:
            return [
                Tool(
                    name="get_access_token",
                    description="获取钉钉 access_token，这是调用其他接口的必要凭证。每个 access_token 的有效期为 7200 秒，有效期内重复获取会返回相同结果，并自动续期。",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                ),
                Tool(
                    name="find_user_by_name",
                    description="根据用户姓名查询用户详细信息。这个工具会：1) 获取所有部门列表；2) 遍历每个部门查找指定姓名的用户；3) 找到后返回用户的详细信息。如果有多个同名用户，会返回找到的第一个用户信息。",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "要查询的用户姓名"
                            }
                        },
                        "required": ["name"]
                    }
                ),
                Tool(
                    name="get_department_list",
                    description="获取企业内部门列表。这是查询用户信息的第一步，通过它可以获取所有部门的 ID。",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                ),
                Tool(
                    name="get_department_users",
                    description="获取部门成员列表。这是查询用户信息的第二步，通过部门 ID 获取该部门下所有用户的基础信息。",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "department_id": {
                                "type": "integer",
                                "description": "部门ID"
                            }
                        },
                        "required": ["department_id"]
                    }
                ),
                Tool(
                    name="get_user_detail",
                    description="获取用户详细信息。这是查询用户信息的最后一步，通过用户 ID 获取用户的所有详细信息。",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "userid": {
                                "type": "string",
                                "description": "用户的 userid"
                            }
                        },
                        "required": ["userid"]
                    }
                ),
                Tool(
                    name="get_calendar_list",
                    description="查询用户的日程列表。可以指定时间范围和最大返回结果数。如果不指定时间范围，默认查询从现在开始7天内的日程。",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "userid": {
                                "type": "string",
                                "description": "要查询日程的用户ID"
                            },
                            "start_time": {
                                "type": "integer",
                                "description": "开始时间的时间戳（毫秒），可选"
                            },
                            "end_time": {
                                "type": "integer",
                                "description": "结束时间的时间戳（毫秒），可选"
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "最大返回结果数，默认50",
                                "default": 50
                            }
                        },
                        "required": ["userid"]
                    }
                )
            ]

        @self.app.call_tool()
        async def call_tool(name: str, arguments: dict) -> List[TextContent]:
            await self.ensure_session()
            
            if name == "get_access_token":
                try:
                    access_token = await self.get_access_token()
                    return [TextContent(type="text", text=f"Access Token: {access_token}")]
                except Exception as e:
                    return [TextContent(type="text", text=f"Error getting access token: {str(e)}")]
            
            elif name == "find_user_by_name":
                try:
                    name = arguments["name"]
                    access_token = await self.get_access_token()
                    
                    # 1. 获取部门列表
                    departments = await self.get_department_list(access_token)
                    
                    # 2. 遍历部门查找用户
                    for dept in departments:
                        users = await self.get_department_users(access_token, dept["id"])
                        for user in users:
                            if user["name"] == name:
                                # 3. 获取用户详细信息
                                user_detail = await self.get_user_detail(access_token, user["userid"])
                                return [TextContent(type="text", text=f"User detail: {json.dumps(user_detail, ensure_ascii=False)}")]
                    
                    return [TextContent(type="text", text=f"User not found: {name}")]
                except Exception as e:
                    return [TextContent(type="text", text=f"Error finding user: {str(e)}")]
            
            elif name == "get_department_list":
                try:
                    access_token = await self.get_access_token()
                    departments = await self.get_department_list(access_token)
                    return [TextContent(type="text", text=f"Department list: {json.dumps(departments, ensure_ascii=False)}")]
                except Exception as e:
                    return [TextContent(type="text", text=f"Error getting department list: {str(e)}")]
            
            elif name == "get_department_users":
                try:
                    access_token = await self.get_access_token()
                    department_id = arguments["department_id"]
                    users = await self.get_department_users(access_token, department_id)
                    return [TextContent(type="text", text=f"Department users: {json.dumps(users, ensure_ascii=False)}")]
                except Exception as e:
                    return [TextContent(type="text", text=f"Error getting department users: {str(e)}")]
            
            elif name == "get_user_detail":
                try:
                    access_token = await self.get_access_token()
                    userid = arguments["userid"]
                    user_detail = await self.get_user_detail(access_token, userid)
                    return [TextContent(type="text", text=f"User detail: {json.dumps(user_detail, ensure_ascii=False)}")]
                except Exception as e:
                    return [TextContent(type="text", text=f"Error getting user detail: {str(e)}")]
            
            elif name == "get_calendar_list":
                try:
                    access_token = await self.get_access_token()
                    userid = arguments["userid"]
                    start_time = arguments.get("start_time")
                    end_time = arguments.get("end_time")
                    max_results = arguments.get("max_results", 50)
                    
                    calendar_list = await self.get_calendar_list(
                        access_token,
                        userid,
                        start_time,
                        end_time,
                        max_results
                    )
                    
                    # 格式化日程信息，使其更易读
                    formatted_events = []
                    for event in calendar_list.get("items", []):
                        formatted_event = {
                            "summary": event.get("summary", "无标题"),
                            "start_time": event.get("start", {}).get("dateTime"),
                            "end_time": event.get("end", {}).get("dateTime"),
                            "location": event.get("location", "无地点"),
                            "organizer": event.get("organizer", {}).get("displayName", "未知"),
                            "description": event.get("description", "无描述")
                        }
                        formatted_events.append(formatted_event)
                    
                    return [TextContent(type="text", text=f"Calendar events: {json.dumps(formatted_events, ensure_ascii=False, indent=2)}")]
                except Exception as e:
                    return [TextContent(type="text", text=f"Error getting calendar list: {str(e)}")]
            
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