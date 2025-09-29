# 使用官方 MinIO 镜像
FROM quay.io/minio/minio:latest

# 设置工作目录
WORKDIR /database

# 暴露端口
EXPOSE 9000 9001

# 设置环境变量
ENV MINIO_ROOT_USER=minioadmin
ENV MINIO_ROOT_PASSWORD=minioadmin

# 创建数据目录
RUN mkdir -p /database

# 启动命令
CMD ["server", "/database", "--console-address", ":9001"]
