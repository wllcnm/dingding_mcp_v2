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
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("dingding_mcp_server")

class DingdingMCPServer:
    def __init__(self):
        logger.info("Initializing DingTalk MCP server...")
        self.app = Server("dingding_mcp_server")
        self.setup_tools()
        self.access_token = None
        self.token_expires = 0
        self.v2_access_token = None
        self.v2_token_expires = 0
        self.session = None
        logger.info("Server initialized successfully")

    async def ensure_session(self):
        if self.session is None:
            logger.debug("Creating new aiohttp session")
            self.session = aiohttp.ClientSession()

    async def get_access_token(self):
        """获取旧版 API 的 access_token"""
        logger.debug("Getting access token...")
        if self.access_token and time.time() < self.token_expires:
            logger.debug("Using cached access token")
            return self.access_token

        await self.ensure_session()
        app_key = os.environ.get("DINGTALK_APP_KEY")
        app_secret = os.environ.get("DINGTALK_APP_SECRET")

        if not all([app_key, app_secret]):
            logger.error("Missing DingTalk API credentials")
            raise ValueError("Missing DingTalk API credentials in environment variables")

        url = "https://oapi.dingtalk.com/gettoken"
        params = {
            "appkey": app_key,
            "appsecret": app_secret
        }
        logger.debug(f"Requesting access token from {url}")

        async with self.session.get(url, params=params) as response:
            data = await response.json()
            logger.debug(f"Access token response: {data}")
            if data.get("errcode") == 0:
                self.access_token = data["access_token"]
                self.token_expires = time.time() + data["expires_in"] - 200
                return self.access_token
            else:
                logger.error(f"Failed to get access token: {data}")
                raise Exception(f"Failed to get access token: {data}")

    async def get_v2_access_token(self):
        """获取新版 API 的 access_token"""
        logger.debug("Getting v2 access token...")
        if self.v2_access_token and time.time() < self.v2_token_expires:
            logger.debug("Using cached v2 access token")
            return self.v2_access_token

        await self.ensure_session()
        app_key = os.environ.get("DINGTALK_APP_KEY")
        app_secret = os.environ.get("DINGTALK_APP_SECRET")

        if not all([app_key, app_secret]):
            logger.error("Missing DingTalk API credentials")
            raise ValueError("Missing DingTalk API credentials in environment variables")

        url = "https://api.dingtalk.com/v1.0/oauth2/accessToken"
        data = {
            "appKey": app_key,
            "appSecret": app_secret
        }
        logger.debug(f"Requesting v2 access token from {url}")

        async with self.session.post(url, json=data) as response:
            result = await response.json()
            logger.debug(f"V2 access token response: {result}")
            if "accessToken" in result:
                self.v2_access_token = result["accessToken"]
                self.v2_token_expires = time.time() + result.get("expireIn", 7200) - 200
                return self.v2_access_token
            else:
                logger.error(f"Failed to get v2 access token: {result}")
                raise Exception(f"Failed to get v2 access token: {result}")

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

    async def get_user_unionid(self, access_token: str, userid: str):
        """获取用户的 unionId"""
        url = "https://oapi.dingtalk.com/topapi/v2/user/get"
        params = {
            "access_token": access_token
        }
        data = {
            "userid": userid
        }
        headers = {
            "Content-Type": "application/json"
        }
        
        async with self.session.post(url, params=params, json=data, headers=headers) as response:
            result = await response.json()
            if result.get("errcode") == 0:
                return result["result"]["unionid"]
            else:
                raise Exception(f"Failed to get user unionid: {result}")

    async def get_calendar_list(self, access_token: str, userid: str, start_time: int = None, end_time: int = None, max_results: int = 50, next_token: str = None):
        """获取用户日程列表"""
        # 1. 先获取用户的 unionId
        unionid = await self.get_user_unionid(access_token, userid)
        
        # 2. 构建日历 API URL
        url = f"https://api.dingtalk.com/v1.0/calendar/users/{unionid}/calendars/primary/events"
        
        # 3. 如果没有指定时间范围，默认查询从现在开始7天内的日程
        if not start_time:
            start_time = int(time.time() * 1000)
        if not end_time:
            end_time = int((time.time() + 7 * 24 * 3600) * 1000)  # 默认7天
        
        params = {
            "maxResults": max_results,
            "timeMin": datetime.fromtimestamp(start_time / 1000).strftime("%Y-%m-%dT%H:%M:%S+08:00"),
            "timeMax": datetime.fromtimestamp(end_time / 1000).strftime("%Y-%m-%dT%H:%M:%S+08:00")
        }
        
        # 4. 添加分页 token
        if next_token:
            params["nextToken"] = next_token
        
        headers = {
            "x-acs-dingtalk-access-token": access_token,
            "Content-Type": "application/json"
        }
        
        logger.debug(f"Requesting calendar list with params: {params}")
        async with self.session.get(url, params=params, headers=headers) as response:
            result = await response.json()
            logger.debug(f"Calendar list response: {result}")
            if "events" in result:
                return result
            else:
                raise Exception(f"Failed to get calendar list: {result}")

    def setup_tools(self):
        logger.info("Setting up tools...")
        
        @self.app.list_tools()
        async def list_tools() -> List[Tool]:
            logger.debug("Listing available tools")
            tools = [
                Tool(
                    name="get_access_token",
                    description="获取钉钉 access_token。当你需要测试 API 连接状态，或者需要手动获取 access_token 时使用此工具。"
                              "注意：通常不需要手动调用此工具，因为其他工具会自动获取和管理 token。"
                              "每个 access_token 的有效期为 7200 秒，有效期内重复获取会返回相同结果，并自动续期。",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                ),
                Tool(
                    name="find_user_by_name",
                    description="根据用户姓名查询用户的详细信息。当你只知道用户的姓名，需要获取该用户的其他信息（如 userid、手机号、邮箱等）时使用此工具。"
                              "此工具会执行以下步骤：1) 获取所有部门列表；2) 遍历每个部门查找指定姓名的用户；3) 返回所有匹配用户的详细信息。"
                              "如果公司内有多个同名用户，会返回所有匹配用户的信息。"
                              "适用场景：根据用户姓名查找其 userid、获取用户联系方式、验证用户身份等。",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "要查询的用户姓名，例如：张三"
                            }
                        },
                        "required": ["name"]
                    }
                ),
                Tool(
                    name="get_department_list",
                    description="获取企业内所有部门的列表信息。当你需要了解公司的组织架构，或者需要获取某个部门的 ID 时使用此工具。"
                              "返回的信息包括：部门ID、部门名称、父部门ID等。"
                              "这通常是查询用户信息的第一步，因为很多其他 API 都需要部门 ID。"
                              "适用场景：获取组织架构、查找部门ID、统计部门数量等。",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                ),
                Tool(
                    name="get_department_users",
                    description="获取指定部门下的所有成员列表。当你需要了解某个部门有哪些成员，或者需要批量获取部门成员信息时使用此工具。"
                              "返回的是成员的基础信息，包括：userid、名字、职位等。"
                              "如果需要某个用户的详细信息，需要再调用 get_user_detail 工具。"
                              "适用场景：统计部门人数、获取部门成员列表、查找部门内特定职位的人员等。",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "department_id": {
                                "type": "integer",
                                "description": "部门的ID，可以通过 get_department_list 工具获取"
                            }
                        },
                        "required": ["department_id"]
                    }
                ),
                Tool(
                    name="get_user_detail",
                    description="获取指定用户的详细信息。当你已经知道用户的 userid，需要获取该用户的详细信息时使用此工具。"
                              "返回的详细信息包括：姓名、手机号、邮箱、所在部门、职位、工号、是否管理员等。"
                              "这是获取用户最完整信息的方法，通常在确认用户身份、获取用户联系方式时使用。"
                              "适用场景：获取用户联系方式、验证用户身份、查询用户所在部门和职位等。",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "userid": {
                                "type": "string",
                                "description": "用户的 userid，例如：202407101414"
                            }
                        },
                        "required": ["userid"]
                    }
                ),
                Tool(
                    name="get_calendar_list",
                    description="查询指定用户的日程列表。当你需要查看用户的日程安排，或者需要了解会议室预订情况时使用此工具。"
                              "支持的功能：1) 按时间范围筛选日程；2) 分页获取日程列表；3) 获取会议详情。"
                              "返回的信息包括：日程标题、开始时间、结束时间、地点、组织者、参与者、会议链接等。"
                              "如果不指定时间范围，默认查询从当前时间开始7天内的日程。"
                              "适用场景：查询用户日程安排、获取会议室预订情况、统计会议时长、导出日程表等。",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "userid": {
                                "type": "string",
                                "description": "要查询日程的用户ID，例如：202407101414"
                            },
                            "start_time": {
                                "type": "integer",
                                "description": "开始时间的时间戳（毫秒），例如：1704067200000 表示 2024-01-01 00:00:00"
                            },
                            "end_time": {
                                "type": "integer",
                                "description": "结束时间的时间戳（毫秒），例如：1704153600000 表示 2024-01-02 00:00:00"
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "单次返回的最大日程数量，默认为 50，建议不要设置太大以免影响性能",
                                "default": 50
                            },
                            "next_token": {
                                "type": "string",
                                "description": "分页标记，从上一次查询结果中获取，用于获取下一页数据"
                            }
                        },
                        "required": ["userid"]
                    }
                )
            ]
            logger.debug(f"Available tools: {[tool.name for tool in tools]}")
            return tools

        @self.app.call_tool()
        async def call_tool(name: str, arguments: dict) -> List[TextContent]:
            logger.info(f"Calling tool: {name} with arguments: {arguments}")
            await self.ensure_session()
            
            try:
                if name == "get_access_token":
                    access_token = await self.get_access_token()
                    return [TextContent(type="text", text=f"Access Token: {access_token}")]
                
                elif name == "find_user_by_name":
                    logger.debug(f"Finding user by name: {arguments['name']}")
                    name = arguments["name"]
                    access_token = await self.get_access_token()
                    
                    found_users = []
                    departments = await self.get_department_list(access_token)
                    
                    for dept in departments:
                        users = await self.get_department_users(access_token, dept["id"])
                        for user in users:
                            if user["name"] == name:
                                user_detail = await self.get_user_detail(access_token, user["userid"])
                                found_users.append(user_detail)
                    
                    if found_users:
                        response = {
                            "total": len(found_users),
                            "users": found_users
                        }
                        return [TextContent(type="text", text=f"Found users: {json.dumps(response, ensure_ascii=False, indent=2)}")]
                    else:
                        return [TextContent(type="text", text=f"User not found: {name}")]

                elif name == "get_department_list":
                    logger.debug("Getting department list")
                    access_token = await self.get_access_token()
                    departments = await self.get_department_list(access_token)
                    return [TextContent(type="text", text=f"Department list: {json.dumps(departments, ensure_ascii=False, indent=2)}")]

                elif name == "get_department_users":
                    logger.debug(f"Getting users for department: {arguments['department_id']}")
                    access_token = await self.get_access_token()
                    department_id = arguments["department_id"]
                    users = await self.get_department_users(access_token, department_id)
                    return [TextContent(type="text", text=f"Department users: {json.dumps(users, ensure_ascii=False, indent=2)}")]

                elif name == "get_user_detail":
                    logger.debug(f"Getting user detail for: {arguments['userid']}")
                    access_token = await self.get_access_token()
                    userid = arguments["userid"]
                    user_detail = await self.get_user_detail(access_token, userid)
                    return [TextContent(type="text", text=f"User detail: {json.dumps(user_detail, ensure_ascii=False, indent=2)}")]
                
                elif name == "get_calendar_list":
                    logger.debug(f"Getting calendar list for user: {arguments['userid']}")
                    access_token = await self.get_v2_access_token()
                    userid = arguments["userid"]
                    start_time = arguments.get("start_time")
                    end_time = arguments.get("end_time")
                    max_results = arguments.get("max_results", 50)
                    next_token = arguments.get("next_token")
                    
                    calendar_list = await self.get_calendar_list(
                        access_token,
                        userid,
                        start_time,
                        end_time,
                        max_results,
                        next_token
                    )
                    
                    formatted_events = []
                    for event in calendar_list.get("events", []):
                        formatted_event = {
                            "summary": event.get("summary", "无标题"),
                            "start_time": event.get("start", {}).get("dateTime"),
                            "end_time": event.get("end", {}).get("dateTime"),
                            "location": event.get("location", {}).get("meetingRooms", ["无地点"])[0] if event.get("location", {}).get("meetingRooms") else "无地点",
                            "organizer": event.get("organizer", {}).get("displayName", "未知"),
                            "description": event.get("description", "无描述"),
                            "status": event.get("status", "未知"),
                            "attendees": [
                                {
                                    "name": attendee.get("displayName", "未知"),
                                    "response": attendee.get("responseStatus", "未知")
                                }
                                for attendee in event.get("attendees", [])
                            ],
                            "online_meeting": event.get("onlineMeetingInfo", {}).get("extraInfo", {}).get("extraUrl", "无会议链接")
                        }
                        formatted_events.append(formatted_event)
                    
                    response = {
                        "events": formatted_events,
                        "next_token": calendar_list.get("nextToken"),
                        "total": len(formatted_events)
                    }
                    
                    return [TextContent(type="text", text=f"Calendar events: {json.dumps(response, ensure_ascii=False, indent=2)}")]
                
                else:
                    logger.warning(f"Unknown tool: {name}")
                    return [TextContent(type="text", text=f"Unknown tool: {name}")]
                    
            except Exception as e:
                logger.error(f"Error calling tool {name}: {str(e)}", exc_info=True)
                return [TextContent(type="text", text=f"Error calling tool {name}: {str(e)}")]

    async def run(self):
        logger.info("Starting DingTalk MCP server...")
        
        async with stdio_server() as (read_stream, write_stream):
            try:
                logger.debug("Initializing MCP server")
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
                    logger.debug("Closing aiohttp session")
                    await self.session.close()

def main():
    logger.info("Starting main function")
    server = DingdingMCPServer()
    asyncio.run(server.run())

if __name__ == "__main__":
    main() 