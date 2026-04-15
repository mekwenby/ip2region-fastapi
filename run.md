### 构建镜像
```bash
docker build -t ip2region-api:latest .
```

### 运行
```bash
docker run -d --name ip2region-api --restart always -m 64m ip2region-api:latest
```