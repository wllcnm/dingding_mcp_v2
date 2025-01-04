import asyncio
import os
import aiohttp
import json
import ssl

async def test_calendar_api():
    # 设置凭证
    app_key = "dingfg84vphtdrlftkv9"
    app_secret = "imHeP0WSQloE_6FwB-GqixrSGa-y5jw0lkZOyzphbC1YPg1b4rmNGwxoPBWIgZmd"
    userid = "202407101414"  # 工号格式

    # 创建 SSL 上下文
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    async with aiohttp.ClientSession() as session:
        # 1. 获取 access token
        token_url = "https://api.dingtalk.com/v1.0/oauth2/accessToken"
        token_data = {
            "appKey": app_key,
            "appSecret": app_secret
        }
        
        print("Getting access token...")
        async with session.post(token_url, json=token_data, ssl=ssl_context) as response:
            token_result = await response.json()
            print(f"Token response: {json.dumps(token_result, indent=2)}")
            
            if "accessToken" not in token_result:
                print("Failed to get access token")
                return
            
            access_token = token_result["accessToken"]

        # 1.5 获取用户 unionId
        user_info_url = "https://oapi.dingtalk.com/topapi/v2/user/get"
        params = {
            "access_token": access_token
        }
        data = {
            "userid": userid
        }
        headers = {
            "Content-Type": "application/json"
        }
        
        print("\nGetting user info...")
        async with session.post(user_info_url, params=params, json=data, headers=headers, ssl=ssl_context) as response:
            user_info = await response.json()
            print(f"User info response: {json.dumps(user_info, indent=2)}")
            
            if user_info.get("errcode") != 0:
                print("Failed to get user info")
                return
            
            union_id = user_info.get("result", {}).get("unionid")
            if not union_id:
                print("No unionid in user info")
                return
        
        # 2. 获取日程列表
        calendar_url = f"https://api.dingtalk.com/v1.0/calendar/users/{union_id}/calendars/primary/events"
        headers = {
            "x-acs-dingtalk-access-token": access_token,
            "Content-Type": "application/json"
        }
        params = {
            "maxResults": 50
        }
        
        print("\nGetting calendar events...")
        async with session.get(calendar_url, params=params, headers=headers, ssl=ssl_context) as response:
            calendar_result = await response.json()
            print(f"Calendar response: {json.dumps(calendar_result, indent=2)}")

if __name__ == "__main__":
    asyncio.run(test_calendar_api()) 