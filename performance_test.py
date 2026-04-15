#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
IP 归属地查询 API 性能测试脚本
测试 LRU 缓存和线程池并发的优化效果
"""

import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_URL = "http://127.0.0.1:5000"

def test_single_ip():
    """测试单个 IP 查询性能"""
    print("\n=== 测试单个 IP 查询 ===")
    
    # 第一次查询（无缓存）
    start = time.time()
    response = requests.get(f"{BASE_URL}/api/ip/8.8.8.8")
    first_time = (time.time() - start) * 1000
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ 首次查询耗时：{first_time:.2f}ms")
        print(f"  IP: {data['data']['ip']}")
        print(f"  归属地：{data['data']['region']}")
    
    # 第二次查询（有缓存）
    start = time.time()
    response = requests.get(f"{BASE_URL}/api/ip/8.8.8.8")
    second_time = (time.time() - start) * 1000
    
    if response.status_code == 200:
        print(f"✓ 缓存查询耗时：{second_time:.2f}ms")
        print(f"  性能提升：{first_time/second_time:.2f}x")
    
    return first_time, second_time


def test_batch_query():
    """测试批量查询性能"""
    print("\n=== 测试批量查询 ===")
    
    test_ips = [
        "8.8.8.8", "1.1.1.1", "114.114.114.114",
        "192.168.1.1", "127.0.0.1", "10.0.0.1",
        "172.16.0.1", "223.5.5.5", "180.76.76.76",
        "1.2.4.8", "8.8.4.4", "9.9.9.9"
    ]
    
    # 串行查询
    start = time.time()
    for ip in test_ips:
        requests.get(f"{BASE_URL}/api/ip/{ip}")
    sequential_time = (time.time() - start) * 1000
    
    # 并发查询（使用线程池）
    start = time.time()
    def query_ip(ip):
        return requests.post(
            f"{BASE_URL}/api/ip",
            json={"ips": [ip]}
        )
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(query_ip, ip) for ip in test_ips]
        for future in as_completed(futures):
            future.result()
    parallel_time = (time.time() - start) * 1000
    
    print(f"✓ 串行查询耗时：{sequential_time:.2f}ms")
    print(f"✓ 并发查询耗时：{parallel_time:.2f}ms")
    print(f"✓ 性能提升：{sequential_time/parallel_time:.2f}x")
    
    return sequential_time, parallel_time


def test_cache_hit_rate():
    """测试缓存命中率"""
    print("\n=== 测试缓存命中率 ===")
    
    # 先清空缓存（通过重启服务，这里简化处理）
    # 查询一组 IP
    test_ips = [f"192.168.{i}.{j}" for i in range(1, 6) for j in range(1, 6)]
    
    for ip in test_ips:
        requests.get(f"{BASE_URL}/api/ip/{ip}")
    
    # 再次查询相同的 IP（应该命中缓存）
    start = time.time()
    hit_count = 0
    for ip in test_ips[:10]:  # 测试前 10 个
        response = requests.get(f"{BASE_URL}/api/ip/{ip}")
        if response.status_code == 200:
            hit_count += 1
    
    cache_time = (time.time() - start) * 1000
    print(f"✓ 缓存查询 10 个 IP 耗时：{cache_time:.2f}ms")
    print(f"✓ 平均每个 IP: {cache_time/10:.2f}ms")
    
    return cache_time


def test_health_check():
    """测试健康检查接口"""
    print("\n=== 健康检查 ===")
    
    response = requests.get(f"{BASE_URL}/health")
    if response.status_code == 200:
        data = response.json()
        print(f"✓ 状态：{data['status']}")
        print(f"✓ 缓存信息：{data['cache_info']}")


def main():
    print("=" * 60)
    print("IP 归属地查询 API 性能测试")
    print("=" * 60)
    
    try:
        # 1. 健康检查
        test_health_check()
        
        # 2. 单 IP 查询测试
        first_time, cached_time = test_single_ip()
        
        # 3. 批量查询测试
        sequential_time, parallel_time = test_batch_query()
        
        # 4. 缓存命中率测试
        cache_time = test_cache_hit_rate()
        
        print("\n" + "=" * 60)
        print("性能测试完成！")
        print("=" * 60)
        print("\n优化效果总结:")
        print(f"  • 缓存加速比：{first_time/cached_time:.2f}x")
        print(f"  • 并发加速比：{sequential_time/parallel_time:.2f}x")
        print(f"  • 批量查询平均：{cache_time/10:.2f}ms/IP")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ 错误：无法连接到 API 服务器")
        print("   请确保 API 正在运行：python main.py")
    except Exception as e:
        print(f"\n❌ 测试失败：{e}")


if __name__ == "__main__":
    main()
