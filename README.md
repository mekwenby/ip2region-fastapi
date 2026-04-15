# ip2region - IP 地理位置查询服务

高性能 IP 地理位置查询 API 服务，基于 [ip2region](https://github.com/lionsoul2014/ip2region) 开源项目。

## 功能特性

- **单 IP 查询** - GET 请求查询单个 IP 的地理位置
- **批量查询** - POST 请求支持最多 1000 个 IP 同时查询
- **高性能** - LRU 缓存 + 异步并发处理
- **IPv4/IPv6** - 支持双协议栈 IP 查询
- **交互式首页** - 友好的 Web 界面直接查询
- **在线演示** - https://ip2region.030399.xyz/

## 快速开始

### 环境要求

- Python >= 3.8

### 安装依赖

```bash
pip install -r requirements.txt
```

### 启动服务

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 5000
```

服务启动后访问 http://localhost:5000

### Docker 部署

```bash
# 构建镜像
docker build -t ip2region-api:latest .

# 运行容器
docker run -d --name ip2region-api -v .:/app -m 64m --restart always -p 5000:5000 ip2region-api:latest
```

或使用 docker-compose：

```bash
docker-compose up -d
```

## API 文档

### 在线交互文档

服务启动后，可通过以下地址访问自动生成的交互式 API 文档：

| 文档类型 | 地址 |
|---------|------|
| **Swagger UI** | http://localhost:5000/docs |
| **ReDoc** | http://localhost:5000/redoc |
| **OpenAPI JSON** | http://localhost:5000/openapi.json |

Swagger UI 支持在线调试 API，直接在页面中输入参数并发送请求。

**注意**: ReDoc 依赖已本地化，无需外部 CDN。

### 单 IP 查询

```
GET /api/ip/{ip}
```

**示例**

```bash
curl http://localhost:5000/api/ip/8.8.8.8
```

**响应**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "ip": "8.8.8.8",
    "region": "United States|California|0|Google LLC|US",
    "country": "United States",
    "province": "California",
    "city": "0",
    "isp": "Google LLC",
    "region_code": "US"
  }
}
```

### 批量查询

```
POST /api/ip
Content-Type: application/json

{
  "ips": ["1.1.1.1", "114.114.114.114"]
}
```

**示例**

```bash
curl -X POST http://localhost:5000/api/ip \
  -H "Content-Type: application/json" \
  -d '{"ips": ["1.1.1.1", "8.8.8.8"]}'
```

**响应**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "results": [...],
    "total": 2,
    "success_count": 2,
    "error_count": 0
  }
}
```

### 健康检查

```
GET /health
```

返回服务状态和缓存命中信息。

## 数据更新

ip2region 使用 `.xdb` 格式的二进制数据库文件。

### 下载官方数据

从 [ip2region Releases](https://github.com/lionsoul2012/ip2region/releases) 下载最新的 `ip2region.xdb` 文件，替换 `data/ip2region_v4.xdb`。

### 文件说明

| 文件 | 说明 |
|------|------|
| `data/ip2region_v4.xdb` | IPv4 数据库 |
| `data/ip2region_v6.xdb` | IPv6 数据库 |
| `data/call_counter.json` | 查询次数统计 |

## 项目结构

```
.
├── main.py              # FastAPI 服务入口
├── python/              # ip2region Python 客户端库
│   └── ip2region/
│       ├── __init__.py
│       ├── searcher.py  # 搜索器实现
│       └── util.py      # 工具函数
├── templates/           # HTML 模板
│   └── index.html       # 主页面
├── static/              # 静态文件目录
├── data/                # 数据目录
│   └── ip2region_v4.xdb # IP 数据库
├── requirements.txt     # Python 依赖
├── Dockerfile           # Docker 配置
└── docker-compose.yml   # Docker Compose 配置
```

## 性能优化

- **LRU 缓存** - 最近查询结果缓存，加速重复查询
- **线程池** - 10 个工作线程并发处理批量请求
- **异步架构** - FastAPI 异步非阻塞设计，高并发支持

## 许可证

基于 [ip2region](https://github.com/lionsoul2014/ip2region) Apache License 2.0
