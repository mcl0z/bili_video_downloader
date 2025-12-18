# Bilibili 视频下载工具

这是一个Bzhan视频下载工具，可以从B站下载视频并自动将音视频流合并为MP4格式。

解析网站：https://bapi.mcl0.top

## 功能特点

- 支持登录用户下载需要权限的视频
- 自动获取视频信息和流媒体URL
- 支持多种视频质量选择（1080p、720p、480p等）
- 自动合并音视频流为MP4文件
- 显示实时下载进度条
- 支持DASH格式和传统格式视频

## 环境要求

- Python 3.7+
- ffmpeg（用于合并音视频流）
- 已保存的Bilibili用户cookies

## 安装依赖

### 安装ffmpeg

在使用本工具前，需要先安装ffmpeg：

**macOS (使用Homebrew):**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**Windows:**
1. 访问 https://ffmpeg.org/download.html 下载Windows版本
2. 解压并添加到系统PATH环境变量中

### 安装Python依赖

确保已安装项目所需的所有Python依赖：

```bash
pip install -r requirements.txt
```

## 使用方法

### 基本用法

```bash
python video_downloader.py <bvid> [quality] [output_dir]
```

参数说明：
- `bvid`: 必需，视频的BV号（例如：BV1xx411c7mu）
- `quality`: 可选，默认为32（480p），指定下载的视频质量
- `output_dir`: 可选，默认为`./downloads`，指定下载文件的保存目录

### 视频质量代码

- 112: 1080p+ (高清)
- 80: 1080p
- 64: 720p
- 32: 480p (默认)
- 16: 360p

### 使用示例

1. 下载默认质量(480p)视频到默认目录：
```bash
python video_downloader.py BV1xx411c7mu
```

2. 下载1080p视频到指定目录：
```bash
python video_downloader.py BV1xx411c7mu 80 ./videos
```

3. 下载720p视频到默认目录：
```bash
python video_downloader.py BV1xx411c7mu 64
```

## Cookies说明

本工具依赖于已保存的Bilibili用户cookies进行身份验证。请确保：

1. 已经通过主程序登录并保存了用户cookies
2. `user_cookies.json`文件存在于项目根目录

工具会自动加载最近保存的用户cookies。

## 输出文件

下载的视频将保存在指定的输出目录中，文件名基于视频标题生成，格式为MP4。

临时文件（分离的视频和音频流）会在合并完成后自动清理。

## 常见问题

### 1. 提示"ffmpeg未找到"

请确保已正确安装ffmpeg并添加到系统PATH中。

### 2. 下载失败或提示权限不足

请确认：
- 已正确保存用户cookies
- 指定的视频BV号正确
- 当前用户有权访问该视频

### 3. 指定的视频质量无法下载

工具会自动选择最接近指定质量的可用质量。如果指定的1080p不可用，可能会自动下载720p或其他较低质量。

## 注意事项

1. 请遵守Bilibili的使用条款和版权规定
2. 不要用于批量下载或商业用途
3. 下载的视频仅供个人学习和参考使用
4. 请尊重视频创作者的版权

## 技术说明

本工具基于项目中已有的Bilibili客户端实现，复用了以下组件：
- `BilibiliClient`: Bilibili API客户端
- `CookieManager`: Cookies管理器

工具工作流程：
1. 加载用户cookies进行身份验证
2. 获取视频信息（标题、CID等）
3. 获取指定质量的视频流URL
4. 分别下载视频和音频流
5. 使用ffmpeg合并音视频为MP4文件
6. 清理临时文件


## 本项目基于MIT开源协议
 
