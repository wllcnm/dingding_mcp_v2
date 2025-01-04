# DingTalk MCP Server V2

这是一个基于 MCP (Model Control Protocol) 的钉钉机器人服务器实现。它提供了与钉钉进行交互的各种功能，包括发送消息、获取会话信息和用户信息等。

## 功能特性

- 发送消息到钉钉会话
- 获取钉钉会话信息
- 获取钉钉用户信息
- 支持多种消息类型（文本、Markdown、链接等）

## 环境要求

- Python 3.10+
- MCP 0.1.0+
- AlibabaCloud DingTalk Stream SDK 1.1.3+

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
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e", "DINGTALK_APP_KEY=你的AppKey",
        "-e", "DINGTALK_APP_SECRET=你的AppSecret",
        "ghcr.io/wllcnm/mcp-dingding-v2:latest"
      ]
    }
  }
}
```

2. 重启 Claude 客户端

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
docker build -t dingding-mcp-v2 .
docker run -e DINGTALK_APP_KEY=your_app_key -e DINGTALK_APP_SECRET=your_app_secret dingding-mcp-v2
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

示例对话：
用户：发送一条消息到钉钉群。
Claude：好的，我来帮你发送消息：
{
  "tool": "send_message",
  "arguments": {
    "conversation_id": "你的群ID",
    "message": "这是一条测试消息"
  }
}

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