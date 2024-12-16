# VideoPreTranscodingForJellyfinOnLinux
# 视频转码服务

## 概述

视频转码服务是一个基于FastAPI构建的Web应用，允许用户上传视频文件，自动进行转码处理，并提供下载和管理已转码文件的功能。该服务支持实时任务状态更新，通过WebSocket实现前端与后端的即时通信，提升用户体验。

## 目录

- [功能](#功能)
- [技术栈](#技术栈)
- [安装](#安装)
- [配置](#配置)
- [使用指南](#使用指南)
  - [启动后端服务器](#启动后端服务器)
  - [访问前端界面](#访问前端界面)
  - [上传视频文件](#上传视频文件)
  - [查看任务列表](#查看任务列表)
  - [下载转码后的视频](#下载转码后的视频)
  - [删除文件](#删除文件)
  - [清空所有文件和任务记录](#清空所有文件和任务记录)
- [API 端点](#api-端点)
- [防火墙配置](#防火墙配置)
- [日志管理](#日志管理)
- [安全性建议](#安全性建议)
- [贡献](#贡献)
- [许可证](#许可证)

## 功能

- **文件上传**：支持批量上传视频文件。
- **自动转码**：使用FFmpeg自动将上传的视频转码为指定格式。
- **实时任务状态**：通过WebSocket实时更新转码任务的状态和进度。
- **文件管理**：查看、下载和删除上传的原始文件、转码后的视频以及生成的ZIP压缩包。
- **清空功能**：一键清空所有文件和任务记录。
- **多线程支持**：配置转码时使用的线程数，提升处理效率。

## 技术栈

- **后端**：
  - [FastAPI](https://fastapi.tiangolo.com/) - 高性能的Web框架
  - [FFmpeg](https://ffmpeg.org/) - 强大的音视频处理工具
  - [SQLModel](https://sqlmodel.tiangolo.com/) - 数据库ORM
  - [Uvicorn](https://www.uvicorn.org/) - ASGI服务器

- **前端**：
  - HTML, CSS, JavaScript

- **操作系统**：
  - Linux

## 安装

### 前提条件

- **Python 3.8+**
- **FFmpeg**：确保系统已安装FFmpeg，并可通过命令行访问。
- **Git**：用于克隆仓库。

### 克隆仓库

```bash
git clone https://github.com/yourusername/video-transcoding-service.git
cd video-transcoding-service
```

### 创建虚拟环境

建议使用虚拟环境隔离项目依赖。

```bash
python3 -m venv venv
source venv/bin/activate
```

### 安装依赖

```bash 
pip install --upgrade pip
pip install -r requirements.txt
```

## 配置

### 创建必要的目录

确保以下目录存在并具有适当的读写权限：

```bash
mkdir -p uploads outputs zips logs
chmod -R 755 uploads outputs zips logs
```

### 防火墙配置

确保服务器开放了8096端口，以允许外部访问。参考[防火墙配置](#防火墙配置)章节了解详细步骤。

## 使用指南

### 启动后端服务器

使用Uvicorn启动FastAPI应用：

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8096
```

或者使用自定义的启动脚本`run.sh`：

```bash
chmod +x run.sh
./run.sh
```

**`run.sh` 示例内容**：

```bash
#!/bin/bash
uvicorn app.main:app --host 0.0.0.0 --port 8096
```

### 访问前端界面

在浏览器中访问：

```
http://<服务器IP>:8096/
```

### 上传视频文件

1. 在“上传文件”部分，点击“选择文件”按钮，选择一个或多个视频文件。
2. 点击“上传”按钮开始上传。
3. 上传过程中，进度条将显示上传进度。
4. 上传完成后，任务列表和文件管理部分将自动刷新，显示新的上传任务和文件。

### 查看任务列表

在“任务列表”部分，可以查看所有转码任务的状态和进度：

- **ID**：任务的唯一标识。
- **文件名**：上传的原始文件名。
- **状态**：任务的当前状态（如`pending`、`processing`、`completed`、`failed`）。
- **进度**：转码任务的完成百分比。
- **操作**：下载链接（如果任务完成）。
- **详细信息**：转码过程中的详细信息（如帧信息）。

### 下载转码后的视频

在“任务列表”或“文件管理”部分，找到状态为`completed`的任务，点击“下载”链接即可下载转码后的视频文件。

### 删除文件

在“文件管理”部分，可以删除上传的原始文件、转码后的视频或生成的ZIP文件：

1. 点击对应文件旁的“删除”按钮。
2. 确认删除操作。
3. 删除成功后，文件管理部分将自动刷新，移除已删除的文件。

### 清空所有文件和任务记录

在“文件管理”部分，点击“清空所有文件和任务记录”按钮：

1. 确认清空操作。
2. 所有上传的文件、转码后的视频及任务记录将被删除。
3. 文件管理部分和任务列表将自动刷新，显示为空。

## API 端点

### 上传文件

- **URL**: `/upload/`
- **方法**: `POST`
- **描述**: 上传一个或多个视频文件，并创建对应的转码任务。
- 请求参数:
  - `files` (form-data): 要上传的文件列表。
- 响应:
  - `200 OK`: 返回已创建的任务列表。

### 获取任务列表

- **URL**: `/tasks/`
- **方法**: `GET`
- **描述**: 获取所有转码任务的列表。
- 响应:
  - `200 OK`: 返回任务列表。

### 下载转码后文件

- **URL**: `/download/{task_id}`
- **方法**: `GET`
- **描述**: 下载指定任务ID对应的转码后视频文件。
- 响应:
  - `200 OK`: 返回视频文件。
  - `404 Not Found`: 文件未找到。

### 下载所有ZIP文件

- **URL**: `/download_zip/`
- **方法**: `GET`
- **描述**: 下载所有完成转码的文件打包成的ZIP文件。
- 响应:
  - `200 OK`: 返回ZIP文件。
  - `404 Not Found`: 无可打包的文件。

### 删除文件

- **URL**: `/files/{file_type}/{filename}`
- **方法**: `DELETE`
- **描述**: 删除指定类型（`upload`、`output`、`zip`）的文件。
- 路径参数:
  - `file_type` (str): 文件类型，`upload`、`output`或`zip`。
  - `filename` (str): 要删除的文件名。
- 响应:
  - `200 OK`: 删除成功。
  - `404 Not Found`: 文件未找到。
  - `400 Bad Request`: 无效的文件类型。

### 清空所有文件和任务记录

- **URL**: `/clear_all/`
- **方法**: `POST`
- **描述**: 删除所有上传的文件、转码后的视频文件以及所有任务记录。
- 响应:
  - `200 OK`: 清空成功。
  - `500 Internal Server Error`: 清空失败。

### 获取任务ID根据输出文件名

- **URL**: `/task_id/{output_filename}`
- **方法**: `GET`
- **描述**: 根据转码后文件名获取对应的任务ID。
- 路径参数:
  - `output_filename` (str): 转码后的视频文件名。
- 响应:
  - `200 OK`: 返回任务ID。
  - `404 Not Found`: 任务未找到。

### WebSocket连接

- **URL**: `/ws`
- **方法**: `GET`
- **描述**: 建立WebSocket连接，用于实时接收转码任务状态更新。

## 防火墙配置

确保服务器开放8096端口，以允许外部访问。以下是针对常见防火墙工具的配置步骤：

### 使用 `ufw`（适用于Ubuntu等基于Debian的系统）

```bash
sudo ufw allow 8096/tcp
sudo ufw reload
sudo ufw status
```

### 使用 `firewalld`（适用于CentOS、Fedora等基于Red Hat的系统）

```bash
sudo firewall-cmd --permanent --add-port=8096/tcp
sudo firewall-cmd --reload
sudo firewall-cmd --list-ports
```

### 使用 `iptables`（适用于各种Linux发行版）

```bash
sudo iptables -A INPUT -p tcp --dport 8096 -j ACCEPT
sudo iptables-save | sudo tee /etc/sysconfig/iptables
```

### 云服务提供商的防火墙配置

如果您的服务器托管在云服务提供商（如AWS、GCP、Azure）上，请在相应的控制台中开放8096端口。

## 日志管理

日志文件存储在`logs`目录中，便于监控和调试。

- **应用日志**：记录应用的运行状态、错误信息和关键事件。
- **转码日志**：记录每个转码任务的详细信息。

### 查看日志

```bash
tail -f logs/app.log
```

## 安全性建议

- **限制来源IP**：如果可能，限制能够访问8096端口的IP范围，避免将端口开放给所有人（即不要使用`0.0.0.0/0`）。
- **使用强密码和认证**：确保应用程序具备适当的认证机制，防止未经授权的访问。
- **使用HTTPS**：在生产环境中，使用HTTPS保护数据传输的安全性。
- **定期更新和补丁**：保持系统和应用程序的更新，修补已知的安全漏洞。
- **监控和日志**：监控端口访问情况，定期查看日志，检测异常活动。

## 贡献

欢迎贡献代码！请按照以下步骤参与：

1. Fork 本仓库。
2. 创建您的功能分支 (`git checkout -b feature/YourFeature`)。
3. 提交您的更改 (`git commit -m 'Add YourFeature'`)。
4. 推送到分支 (`git push origin feature/YourFeature`)。
5. 创建一个新的Pull Request。

## 许可证

本项目采用 MIT 许可证。
=======

# VideoPreTranscodingForJellyfinOnLinux

使用linux服务器为Jellyfin视频离线转码

>>>>>>> 066a470ccfdf12bfdc3c59390a6fa17908ad2cb8
