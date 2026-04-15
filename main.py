from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from typing import Optional, List
import sys
import os
import json
import threading
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor
from ipaddress import ip_address, IPv6Address

# 添加本地 python 目录到路径，使用本地的 ip2region 模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'python'))

from ip2region import Ip2Region

app = FastAPI(
    title="ip2region API",
    description="高性能 IP 地理位置查询服务，支持 IPv4/IPv6 单IP查询和批量查询",
    version="1.0.0",
    docs_url="/docs",
    redoc_url=None,
    openapi_url="/openapi.json"
)

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory="static"), name="static")

# 模板引擎
templates = Jinja2Templates(directory="templates")

# 初始化 IP 数据库
db_path = os.path.join(os.path.dirname(__file__), "data", "ip2region_v4.xdb")
searcher = Ip2Region(db_path)

# 初始化 IPv6 数据库
db_path_v6 = os.path.join(os.path.dirname(__file__), "data", "ip2region_v6.xdb")
searcher_v6 = Ip2Region(db_path_v6)

# 调用次数持久化配置
COUNTER_FILE = os.path.join(os.path.dirname(__file__), "data", "call_counter.json")
counter_lock = threading.Lock()

# 线程池用于并发处理批量查询
executor = ThreadPoolExecutor(max_workers=10)


# ============== Pydantic Models ==============

class IPRegionData(BaseModel):
    """单个 IP 归属地信息"""
    ip: str = Field(description="IP地址")
    region: str = Field(description="完整归属地字符串，格式：国家|省/州|城市|ISP|区域代码")
    country: str = Field(description="国家/地区")
    province: str = Field(description="省/州")
    city: str = Field(description="城市")
    isp: str = Field(description="运营商")
    region_code: str = Field(description="区域代码")


class IPSingleResponse(BaseModel):
    """单IP查询响应"""
    code: int = Field(description="状态码，200表示成功")
    message: str = Field(description="响应信息")
    data: Optional[IPRegionData] = Field(description="归属地数据")


class BatchResultItem(BaseModel):
    """批量查询结果项"""
    ip: str = Field(description="IP地址")
    region: Optional[str] = Field(description="完整归属地字符串")
    country: Optional[str] = Field(description="国家/地区")
    province: Optional[str] = Field(description="省/州")
    city: Optional[str] = Field(description="城市")
    isp: Optional[str] = Field(description="运营商")
    region_code: Optional[str] = Field(description="区域代码")
    error: Optional[str] = Field(description="查询错误信息")


class BatchResponseData(BaseModel):
    """批量查询响应数据"""
    results: List[BatchResultItem] = Field(description="查询结果列表")
    total: int = Field(description="总查询数")
    success_count: int = Field(description="成功数量")
    error_count: int = Field(description="失败数量")


class BatchResponse(BaseModel):
    """批量查询响应"""
    code: int = Field(description="状态码，200表示成功")
    message: str = Field(description="响应信息")
    data: BatchResponseData


class ErrorResponse(BaseModel):
    """错误响应"""
    code: int = Field(description="错误码")
    message: str = Field(description="错误信息")
    data: Optional[None] = Field(default=None, description="数据为空")


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str = Field(description="服务状态")
    total_calls: int = Field(description="总查询次数")
    cache_info: str = Field(description="缓存状态信息")


class IPLists(BaseModel):
    """批量查询请求模型"""
    ips: List[str] = Field(min_length=1, max_length=1000, description="IP 地址列表，最多 1000 个")


# ============== Helper Functions ==============

def load_counter():
    """从文件加载调用计数"""
    try:
        if os.path.exists(COUNTER_FILE):
            with open(COUNTER_FILE, 'r') as f:
                data = json.load(f)
                return data.get('total_calls', 0)
    except Exception:
        pass
    return 0


def save_counter(count):
    """保存调用计数到文件"""
    try:
        with open(COUNTER_FILE, 'w') as f:
            json.dump({'total_calls': count}, f)
    except Exception:
        pass


def increment_counter():
    """原子性增加调用计数"""
    with counter_lock:
        count = load_counter()
        count += 1
        save_counter(count)
        return count


# 加载初始计数
total_calls = load_counter()


def is_valid_ip(ip: str) -> bool:
    """IP 地址验证函数（支持 IPv4 和 IPv6）"""
    try:
        ip_address(ip)
        return True
    except ValueError:
        return False


def parse_region(region_str: str) -> dict:
    """
    解析 region 字符串为独立字段
    格式: 国家|省/州|城市|ISP|区域代码
    """
    parts = region_str.split('|') if region_str else []
    return {
        'country': parts[0] if len(parts) > 0 else '',
        'province': parts[1] if len(parts) > 1 else '',
        'city': parts[2] if len(parts) > 2 else '',
        'isp': parts[3] if len(parts) > 3 else '',
        'region_code': parts[4] if len(parts) > 4 else ''
    }


@lru_cache(maxsize=1000)
def cached_search(ip: str) -> str:
    """带缓存的 IP 查询函数"""
    ip_obj = ip_address(ip)
    if isinstance(ip_obj, IPv6Address):
        return searcher_v6.search(ip)
    return searcher.search(ip)


# ============== API Endpoints ==============

def get_client_ip(request: Request) -> str:
    """获取客户端 IP 地址"""
    # 优先从代理头获取
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    if request.client:
        return request.client.host
    return "127.0.0.1"


@app.get("/", response_class=HTMLResponse, tags=["首页"])
async def index(request: Request):
    """
    ip2region 首页
    - 返回交互式 Web 查询界面
    - 自动获取访问者 IP 并查询
    """
    client_ip = get_client_ip(request)
    return templates.TemplateResponse("index.html", {"request": request, "client_ip": client_ip})


@app.get("/api/ip/", tags=["IP 查询"])
async def get_my_ip(request: Request):
    """
    获取当前请求的客户端 IP 地址
    """
    client_ip = get_client_ip(request)
    return {"ip": client_ip}


@app.get("/redoc", response_class=HTMLResponse, tags=["文档"])
async def redoc_page(request: Request):
    """
    ReDoc API 文档页面
    """
    return templates.TemplateResponse("redoc.html", {"request": request})


@app.get(
    "/api/ip/{ip_address}",
    response_model=IPSingleResponse,
    summary="查询单个 IP 归属地",
    description="根据 IP 地址查询其地理位置信息，支持 IPv4 和 IPv6 地址",
    responses={
        200: {"description": "查询成功", "model": IPSingleResponse},
        400: {"description": "无效的 IP 地址格式", "model": ErrorResponse}
    },
    tags=["IP 查询"]
)
async def query_ip(ip_address: str):
    """
    查询单个 IP 的地理位置归属地信息

    **支持格式：**
    - IPv4：如 `8.8.8.8`、`114.114.114.114`
    - IPv6：如 `2001:4860:4860::8888`、`2404:6800:4008::`

    **返回字段说明：**
    - `region`: 完整归属地字符串，格式为 `国家|省/州|城市|ISP|区域代码`
    - `country`: 国家/地区名称
    - `province`: 省/州
    - `city`: 城市
    - `isp`: 运营商
    - `region_code`: 区域代码（国家代码）
    """
    increment_counter()

    if not is_valid_ip(ip_address):
        return JSONResponse(
            status_code=400,
            content={
                'code': 400,
                'message': '无效的 IP 地址格式',
                'data': None
            }
        )

    try:
        region = cached_search(ip_address)
        region_info = parse_region(region)
        return {
            'code': 200,
            'message': 'success',
            'data': {
                'ip': ip_address,
                'region': region,
                'country': region_info['country'],
                'province': region_info['province'],
                'city': region_info['city'],
                'isp': region_info['isp'],
                'region_code': region_info['region_code']
            }
        }
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={
                'code': 400,
                'message': str(e),
                'data': None
            }
        )


@app.post(
    "/api/ip",
    response_model=BatchResponse,
    summary="批量查询 IP 归属地",
    description="一次请求查询多个 IP 的地理位置信息，最多支持 1000 个 IP",
    responses={
        200: {"description": "查询成功", "model": BatchResponse},
        400: {"description": "请求参数错误", "model": ErrorResponse},
        500: {"description": "服务器内部错误", "model": ErrorResponse}
    },
    tags=["IP 查询"]
)
async def query_ip_batch(data: IPLists):
    """
    批量查询多个 IP 的地理位置归属地信息

    **请求示例：**
    ```json
    {
        "ips": ["8.8.8.8", "1.1.1.1", "114.114.114.114"]
    }
    ```

    **限制说明：**
    - 每次最多查询 1000 个 IP
    - 每个 IP 单独计费（计入总查询次数）

    **返回字段说明：**
    - `results`: 查询结果列表，每个元素包含单个 IP 的归属地信息
    - `total`: 请求的 IP 总数
    - `success_count`: 成功查询的数量
    - `error_count`: 查询失败的数量
    - `error`: 如果查询失败，包含错误原因
    """
    try:
        ip_list = data.ips

        if not ip_list:
            return JSONResponse(
                status_code=400,
                content={
                    'code': 400,
                    'message': 'ips 参数不能为空',
                    'data': None
                }
            )

        if len(ip_list) > 1000:
            return JSONResponse(
                status_code=400,
                content={
                    'code': 400,
                    'message': '单次查询最多支持 1000 个 IP',
                    'data': None
                }
            )

        # 增加调用计数（每个 IP 一次）
        for _ in range(len(ip_list)):
            increment_counter()

        def search_single_ip(ip: str):
            try:
                if not is_valid_ip(ip):
                    return {
                        'ip': ip,
                        'region': None,
                        'country': None,
                        'province': None,
                        'city': None,
                        'isp': None,
                        'region_code': None,
                        'error': '无效的 IP 地址格式'
                    }
                region = cached_search(ip)
                region_info = parse_region(region)
                return {
                    'ip': ip,
                    'region': region,
                    'country': region_info['country'],
                    'province': region_info['province'],
                    'city': region_info['city'],
                    'isp': region_info['isp'],
                    'region_code': region_info['region_code']
                }
            except Exception as e:
                return {
                    'ip': ip,
                    'region': None,
                    'country': None,
                    'province': None,
                    'city': None,
                    'isp': None,
                    'region_code': None,
                    'error': str(e)
                }

        results = list(executor.map(search_single_ip, ip_list))

        success_count = sum(1 for r in results if r.get('region') and not r.get('error'))
        error_count = len(results) - success_count

        return {
            'code': 200,
            'message': 'success',
            'data': {
                'results': results,
                'total': len(results),
                'success_count': success_count,
                'error_count': error_count
            }
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                'code': 500,
                'message': str(e),
                'data': None
            }
        )


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="健康检查",
    description="检查服务状态，返回缓存统计和总查询次数",
    tags=["系统"]
)
async def health_check():
    """
    健康检查接口

    **返回信息：**
    - `status`: 服务状态，固定为 "healthy"
    - `total_calls`: 服务启动以来的总查询次数
    - `cache_info`: LRU 缓存状态，包含 hits/misses/currsize/maxsize
    """
    global total_calls
    total_calls = load_counter()
    return {
        'status': 'healthy',
        'total_calls': total_calls,
        'cache_info': str(cached_search.cache_info())
    }


if __name__ == '__main__':
    import uvicorn
    print("IP 归属地查询 API 启动中...")
    print("优化特性：LRU 缓存 + 线程池并发 + IP 格式预检")
    uvicorn.run(app, host='0.0.0.0', port=5000)
