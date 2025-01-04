# DingTalk MCP Server V2

这是一个基于 MCP (Model Control Protocol) 的钉钉机器人服务器实现。它提供了与钉钉进行交互的各种功能，包括发送消息、获取会话信息、用户信息和日历事件等。

## 功能特性

- 发送消息到钉钉会话
- 获取钉钉会话信息
- 获取钉钉用户信息
- 查询用户日历事件
- 支持多种消息类型（文本、Markdown、链接等）

## 环境要求

- Python 3.10+
- MCP 0.1.0+
- aiohttp 3.9.1+

## 环境变量配置

使用前需要设置以下环境变量：

- `DINGTALK_APP_KEY`: 钉钉应用的 AppKey
- `DINGTALK_APP_SECRET`: 钉钉应用的 AppSecret

## 在 Claude 客户端中使用

1. 在你的 `claude_desktop_config.json` 中添加以下配置：
```json
{
  "mcpServers": {
    "dingding": {
      "command": "sh",
      "args": [
        "-c",
        "docker ps -a | grep mcp-dingding-v2 | awk '{print $1}' | xargs -r docker rm -f > /dev/null 2>&1; docker pull ghcr.io/wllcnm/mcp-dingding-v2:latest > /dev/null 2>&1; docker run -i --rm --name mcp-dingding-v2 -e DINGTALK_APP_KEY=你的AppKey -e DINGTALK_APP_SECRET=你的AppSecret ghcr.io/wllcnm/mcp-dingding-v2:latest"
      ]
    }
  }
}
```

2. 重启 Claude 客户端

注意：上面的启动命令会：
1. 查找并删除所有旧的 mcp-dingding-v2 容器
2. 从 GitHub 拉取最新的镜像
3. 使用 `--name` 参数给容器指定固定名称
4. 使用 `--rm` 参数在容器停止时自动删除

命令说明：
- `docker ps -a | grep mcp-dingding-v2 | awk '{print $1}' | xargs -r docker rm -f`: 删除所有旧容器
- `docker pull ghcr.io/wllcnm/mcp-dingding-v2:latest`: 拉取最新镜像
- `docker run -i --rm --name mcp-dingding-v2 ...`: 运行新容器
- `> /dev/null 2>&1`: 隐藏不必要的输出信息

## 本地开发

### 安装

```bash
pip install -r requirements.txt
```

### 运行

直接运行服务器：
```bash
python src/server.py
```

使用 Docker 运行：
```bash
# 清理旧容器
docker ps -a | grep mcp-dingding-v2 | awk '{print $1}' | xargs -r docker rm -f

# 构建并运行新容器
docker build -t dingding-mcp-v2 .
docker run -i --rm --name mcp-dingding-v2 \
  -e DINGTALK_APP_KEY=your_app_key \
  -e DINGTALK_APP_SECRET=your_app_secret \
  dingding-mcp-v2
```

## API 工具

### 1. send_message
发送消息到钉钉会话
- 参数：
  - conversation_id: 会话 ID
  - message: 消息内容
  - msg_type: 消息类型（可选，默认为 text）

### 2. get_conversation_info
获取钉钉会话信息
- 参数：
  - conversation_id: 会话 ID

### 3. get_user_info
获取钉钉用户信息
- 参数：
  - user_id: 用户 ID

### 4. get_calendar_list
查询用户的日历事件列表
- 参数：
  - userid: 用户 ID（必填）
  - start_time: 开始时间的时间戳（毫秒，可选）
  - end_time: 结束时间的时间戳（毫秒，可选）
  - max_results: 最大返回结果数（可选，默认 50）
  - next_token: 分页 token（可选）
- 返回：
  - events: 日历事件列表
    - summary: 事件标题
    - start_time: 开始时间
    - end_time: 结束时间
    - location: 地点
    - organizer: 组织者
    - description: 描述
    - status: 状态
    - attendees: 参与者列表
  - next_token: 下一页的 token
  - total: 本次返回的事件数量

## 使用示例

在 Claude 中，你可以这样使用工具：

```json
{
  "tool": "send_message",
  "arguments": {
    "conversation_id": "你的会话ID",
    "message": "Hello, DingTalk!",
    "msg_type": "text"
  }
}
```

查询日历示例：
```json
{
  "tool": "get_calendar_list",
  "arguments": {
    "userid": "用户ID",
    "start_time": 1704067200000,  // 2024-01-01 00:00:00
    "end_time": 1704153600000,    // 2024-01-02 00:00:00
    "max_results": 10
  }
}
```

## 注意事项

1. 安全性
   - 请妥善保管你的钉钉 API 凭证
   - 不要在公共场合分享你的配置文件
   - 建议使用环境变量而不是硬编码凭证

2. 故障排除
   - 检查 API 凭证是否正确
   - 确保网络连接正常
   - 查看日志输出了解详细错误信息

## 许可证

MIT 