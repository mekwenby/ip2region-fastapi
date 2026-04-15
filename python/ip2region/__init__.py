# Copyright 2022 The Ip2Region Authors. All rights reserved.
# Use of this source code is governed by a Apache2.0-style
# license that can be found in the LICENSE file.

# xdb package

from .searcher import Searcher, new_with_file_only, new_with_vector_index, new_with_buffer
from .util import IPv4, IPv6, Header, load_header_from_file, version_from_header

# 便捷类，用于创建 Searcher 实例
class Ip2Region:
    def __init__(self, db_path: str):
        """
        初始化 IP2Region 查询器
        :param db_path: xdb 数据库文件路径
        """
        # 从数据库文件头自动检测 IP 版本
        header = load_header_from_file(db_path)
        version = version_from_header(header)
        self.searcher = new_with_file_only(version, db_path)
    
    def search(self, ip: str):
        """
        查询 IP 归属地
        :param ip: IP 地址
        :return: 归属地信息字符串
        """
        return self.searcher.search(ip)
    
    def close(self):
        """关闭查询器"""
        if self.searcher:
            self.searcher.close()