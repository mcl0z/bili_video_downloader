
import asyncio
import json
import os
import sys
import httpx
from pathlib import Path
from typing import Dict, Any, Optional
import subprocess

# 添加项目路径到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.bilibili.client import BilibiliClient
from backend.utils.cookie_manager import cookie_manager
from backend.bilibili.auth import BilibiliAuth

class VideoDownloader:
    """Bilibili视频下载器"""
    
    def __init__(self, cookie_file: str = "user_cookies.json"):
        self.cookie_file = Path(cookie_file)
        self.client = None
        self.cookies = None
        
    def load_cookies(self) -> bool:
        """加载用户cookies"""
        try:
            if not self.cookie_file.exists():
                print(f"找不到cookie文件 {self.cookie_file}，将启动扫码登录")
                return self.qr_login()
                
            cookie_manager.load_cookies()
            users = cookie_manager.get_all_users()
            
            if not users:
                print("没有找到已保存的用户，将启动扫码登录")
                return self.qr_login()
            
            # 使用最近保存的用户
            latest_user = max(users.items(), key=lambda x: x[1]['saved_time'])
            user_id, user_data = latest_user
            
            self.cookies = cookie_manager.get_cookies(user_id)
            if not self.cookies:
                print("无法获取用户cookies，将启动扫码登录")
                return self.qr_login()
                
            print(f"已加载用户: {user_data['user_info'].get('uname', user_id)}")
            return True
        except Exception as e:
            print(f"加载cookies失败: {e}")
            return False
    
    def qr_login(self) -> bool:
        """扫码登录"""
        try:
            # 在已有的事件循环中执行或创建新的事件循环
            try:
                # 尝试获取当前事件循环
                loop = asyncio.get_running_loop()
            except RuntimeError:
                # 如果没有正在运行的事件循环，则创建新的
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(self._qr_login_async())
                loop.close()
                return result
            else:
                # 在已有的事件循环中执行
                # 使用 asyncio.create_task 或直接 await
                task = loop.create_task(self._qr_login_async())
                # 在 Jupyter 或其他已有事件循环环境中运行
                # 需要特殊处理
                try:
                    import nest_asyncio
                    nest_asyncio.apply()
                    result = loop.run_until_complete(task)
                    return result
                except:
                    # 如果 nest_asyncio 不可用或失败，尝试不同的方法
                    result = asyncio.run(self._qr_login_async())
                    return result
        except Exception as e:
            print(f"扫码登录失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def _qr_login_async(self) -> bool:
        """异步执行扫码登录"""
        try:
            async with BilibiliAuth() as auth:
                # 获取二维码
                print("正在生成二维码...")
                qr_data = await auth.login_with_qr()
                
                if qr_data['status'] != 'qr_ready':
                    print(f"获取二维码失败: {qr_data['message']}")
                    return False
                
                # 显示二维码
                qr_image_data = qr_data['qr_image']
                qrcode_key = qr_data['qrcode_key']
                
                # 将base64数据写入临时文件以供显示
                import base64
                from PIL import Image
                import io
                
                try:
                    # 解码base64数据
                    header, encoded = qr_image_data.split(",", 1)
                    qr_bytes = base64.b64decode(encoded)
                    
                    # 创建PIL图像
                    image = Image.open(io.BytesIO(qr_bytes))
                    
                    # 保存到临时文件
                    qr_filename = "bilibili_qr.png"
                    image.save(qr_filename)
                    print(f"二维码已保存为 {qr_filename}，请使用Bilibili手机客户端扫描")
                    
                    # 尝试在终端中显示二维码
                    self._display_qr_in_terminal(image)
                except Exception as e:
                    print(f"无法显示二维码图片: {e}")
                    print("请使用Bilibili手机客户端扫描以下链接:")
                    print(f"二维码Key: {qrcode_key}")
                    # 在某些系统上可以尝试打开图片
                    try:
                        import webbrowser
                        import os
                        webbrowser.open(f"file://{os.path.abspath(qr_filename)}")
                    except:
                        pass
                
                # 轮询检查扫码状态
                max_attempts = 100  # 最大尝试次数
                attempt = 0
                
                while attempt < max_attempts:
                    status = await auth.check_qr_status(qrcode_key)
                    
                    if status['status'] == 'success':
                        print("登录成功!")
                        
                        # 保存cookies
                        cookies = status['cookies']
                        # 获取用户信息
                        user_info = await self._get_user_info_with_cookies(cookies)
                        user_id = user_info.get('mid', 'unknown_user')
                        
                        # 保存到cookie管理器
                        cookie_manager.save_cookies(user_id, cookies, user_info)
                        
                        # 更新当前实例的cookies
                        self.cookies = cookies
                        print(f"已保存用户: {user_info.get('uname', user_id)}")
                        # 清理临时二维码文件
                        try:
                            if os.path.exists("bilibili_qr.png"):
                                os.remove("bilibili_qr.png")
                        except:
                            pass
                        return True
                        
                    elif status['status'] == 'waiting':
                        print("等待扫码...")
                    elif status['status'] == 'scanned':
                        print("已扫码，等待确认...")
                    elif status['status'] == 'expired':
                        print("二维码已过期，请重新运行程序")
                        # 清理临时二维码文件
                        try:
                            if os.path.exists("bilibili_qr.png"):
                                os.remove("bilibili_qr.png")
                        except:
                            pass
                        return False
                    else:
                        print(f"登录出错: {status['message']}")
                        # 清理临时二维码文件
                        try:
                            if os.path.exists("bilibili_qr.png"):
                                os.remove("bilibili_qr.png")
                        except:
                            pass
                        return False
                    
                    attempt += 1
                    await asyncio.sleep(3)  # 每3秒检查一次
                
                print("登录超时，请重新运行程序")
                # 清理临时二维码文件
                try:
                    if os.path.exists("bilibili_qr.png"):
                        os.remove("bilibili_qr.png")
                except:
                    pass
                return False
                
        except Exception as e:
            print(f"扫码登录异常: {e}")
            # 清理临时二维码文件
            try:
                if os.path.exists("bilibili_qr.png"):
                    os.remove("bilibili_qr.png")
            except:
                pass
            return False
    
    def _display_qr_in_terminal(self, image):
        """在终端中显示二维码"""
        try:
            # 缩小图片以适应终端
            width, height = image.size
            aspect_ratio = height / width
            new_width = 40
            new_height = int(aspect_ratio * new_width * 0.5)
            image = image.resize((new_width, new_height))
            
            # 转换为灰度图
            image = image.convert('L')
            
            # 定义字符集，用于表示不同的灰度级
            chars = [" ", "░", "▒", "▓", "█"]
            
            print("\n扫码登录二维码:")
            print("+" + "-" * new_width + "+")
            
            for y in range(new_height):
                line = "|"
                for x in range(new_width):
                    pixel = image.getpixel((x, y))
                    # 将256级灰度映射到字符集
                    char_index = min(pixel // 51, len(chars) - 1)  # 256 / 5 = 51
                    line += chars[char_index]
                line += "|"
                print(line)
            
            print("+" + "-" * new_width + "+")
            print("请使用Bilibili手机客户端扫描上面的二维码\n")
        except Exception as e:
            print(f"无法在终端中显示二维码: {e}")

    async def _get_user_info_with_cookies(self, cookies: Dict[str, str]) -> Dict[str, Any]:
        """使用cookies获取用户信息"""
        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Referer': 'https://www.bilibili.com/'
                }
                
                # 设置cookies
                for key, value in cookies.items():
                    client.cookies.set(key, value)
                
                response = await client.get('https://api.bilibili.com/x/web-interface/nav', headers=headers)
                data = response.json()
                
                if data['code'] == 0:
                    return data['data']
                else:
                    return {}
        except Exception as e:
            print(f"获取用户信息失败: {e}")
            return {}

    async def init_client(self):
        """初始化Bilibili客户端"""
        if not self.cookies:
            if not self.load_cookies():
                return False
                
        self.client = BilibiliClient()
        self.client.set_cookies(self.cookies)
        # 获取WBI密钥
        await self.client.get_wbi_keys()
        return True
    
    async def get_video_info(self, bvid: str) -> Optional[Dict[Any, Any]]:
        """获取视频信息"""
        if not self.client:
            await self.init_client()
            
        try:
            result = await self.client.get_video_info(bvid=bvid)
            if result.get('code') == 0:
                return result
            else:
                print(f"获取视频信息失败: {result.get('message')}")
                return None
        except Exception as e:
            print(f"获取视频信息异常: {e}")
            return None
    
    async def get_video_stream(self, bvid: str, cid: int, quality: int = 32) -> Optional[Dict[Any, Any]]:
        """获取视频流信息"""
        if not self.client:
            await self.init_client()
            
        try:
            result = await self.client.get_video_stream_url(bvid=bvid, cid=cid, qn=quality)
            if result.get('code') == 0:
                return result
            else:
                print(f"获取视频流失败: {result.get('message')}")
                return None
        except Exception as e:
            print(f"获取视频流异常: {e}")
            return None
    
    def progress_callback(self, progress: int, total: int, prefix: str = ''):
        """显示下载进度"""
        if total == 0:
            return
            
        percent = 100 * progress / total
        bar_length = 40
        filled_length = int(bar_length * progress // total)
        bar = '█' * filled_length + '-' * (bar_length - filled_length)
        
        # 打印进度条
        print(f'\r{prefix} |{bar}| {percent:.1f}% ({progress / 1024 / 1024:.1f}MB / {total / 1024 / 1024:.1f}MB)', end='')
        
        # 如果完成，换行
        if progress == total:
            print()
    
    async def download_stream(self, url: str, filename: str) -> bool:
        """下载视频/音频流"""
        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Referer': 'https://www.bilibili.com/'
                }
                
                async with client.stream('GET', url, headers=headers) as response:
                    response.raise_for_status()
                    total_size = int(response.headers.get('content-length', 0))
                    
                    downloaded = 0
                    with open(filename, 'wb') as f:
                        async for chunk in response.aiter_bytes(chunk_size=8192):
                            f.write(chunk)
                            downloaded += len(chunk)
                            
                            # 显示进度条
                            if total_size > 0:
                                self.progress_callback(downloaded, total_size, f"下载 {os.path.basename(filename)}:")
                                
            print(f"已下载: {filename}")
            return True
        except Exception as e:
            print(f"\n下载 {filename} 失败: {e}")
            return False
    
    def merge_video_audio(self, video_file: str, audio_file: str, output_file: str) -> bool:
        """合并视频和音频文件"""
        try:
            # 检查ffmpeg是否可用
            try:
                subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                print("错误: 未找到ffmpeg，请先安装ffmpeg")
                return False
            
            print("正在合并音视频...")
            # 使用ffmpeg合并音视频
            cmd = [
                'ffmpeg', '-i', video_file, '-i', audio_file,
                '-c:v', 'copy', '-c:a', 'copy', '-y', output_file
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"合并失败: {result.stderr}")
                return False
                
            print(f"已合并为: {output_file}")
            return True
        except Exception as e:
            print(f"合并音视频失败: {e}")
            return False
        finally:
            # 清理临时文件
            try:
                if os.path.exists(video_file):
                    os.remove(video_file)
                if os.path.exists(audio_file):
                    os.remove(audio_file)
            except Exception as e:
                print(f"清理临时文件失败: {e}")
    
    async def download_video(self, bvid: str, quality: int = 32, output_dir: str = "./downloads") -> bool:
        """下载Bilibili视频"""
        print(f"开始下载视频: {bvid}")
        
        # 创建输出目录
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # 获取视频信息
        video_info = await self.get_video_info(bvid)
        if not video_info:
            return False
            
        title = video_info['data']['title']
        cid = video_info['data']['cid']
        print(f"视频标题: {title}")
        print(f"视频CID: {cid}")
        
        # 获取视频流
        stream_info = await self.get_video_stream(bvid, cid, quality)
        if not stream_info:
            return False
            
        # 检查数据结构
        if 'data' not in stream_info:
            print(f"流信息结构异常: {stream_info}")
            return False
            
        # 获取数据部分
        data = stream_info['data']
        
        # 处理DASH格式视频
        if 'dash' in data:
            dash = data['dash']
            
            # 获取最佳视频和音频流
            video_stream = None
            audio_stream = None
            
            # 选择视频流
            if dash.get('video'):
                # 选择指定质量的视频流，如果没有则选择最接近的较低质量
                for stream in dash['video']:
                    if stream['id'] == quality:
                        video_stream = stream
                        break
                
                # 如果没有找到指定质量，则选择最接近的较低质量
                if not video_stream:
                    available_qualities = [stream['id'] for stream in dash['video']]
                    available_qualities.sort(reverse=True)  # 从高到低排序
                    
                    # 选择不超过指定质量的最高质量
                    for q in available_qualities:
                        if q <= quality:
                            for stream in dash['video']:
                                if stream['id'] == q:
                                    video_stream = stream
                                    quality = q  # 更新实际使用的质量
                                    break
                            break
                
                # 如果还是没有找到，则选择最高质量
                if not video_stream and dash['video']:
                    video_stream = dash['video'][0]
                    quality = video_stream['id']
                        
            # 选择音频流
            if dash.get('audio'):
                # 选择最高质量的音频流
                audio_stream = dash['audio'][0]
                
            if not video_stream or not audio_stream:
                print("无法找到合适的视频或音频流")
                return False
                
            print(f"视频流质量: {video_stream['id']}")
            print(f"音频流质量: {audio_stream['id']}")
            
            # 生成文件名
            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            video_file = os.path.join(output_dir, f"{safe_title}_video.m4s")
            audio_file = os.path.join(output_dir, f"{safe_title}_audio.m4s")
            output_file = os.path.join(output_dir, f"{safe_title}.mp4")
            
            # 下载视频流
            print("正在下载视频流...")
            if not await self.download_stream(video_stream['baseUrl'], video_file):
                return False
                
            # 下载音频流
            print("正在下载音频流...")
            if not await self.download_stream(audio_stream['baseUrl'], audio_file):
                return False
                
            # 合并音视频
            if not self.merge_video_audio(video_file, audio_file, output_file):
                return False
                
            print(f"视频下载完成: {output_file}")
            return True
            
        # 处理非DASH格式视频（传统格式）
        elif 'durl' in data:
            print("处理传统格式视频...")
            durl = data['durl']
            
            if not durl:
                print("未找到可下载的视频链接")
                return False
                
            # 生成文件名
            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            output_file = os.path.join(output_dir, f"{safe_title}.mp4")
            
            # 下载视频（通常已包含音频）
            video_url = durl[0]['url']
            print("正在下载视频...")
            if not await self.download_stream(video_url, output_file):
                return False
                
            print(f"视频下载完成: {output_file}")
            return True
            
        else:
            print("不支持的视频格式")
            print(f"可用的数据键: {list(data.keys())}")
            return False


async def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("使用方法: python video_downloader.py <bvid> [quality] [output_dir]")
        print("示例: python video_downloader.py BV1xx411c7mu")
        print("示例: python video_downloader.py BV1xx411c7mu 32 ./videos")
        return
    
    bvid = sys.argv[1]
    quality = int(sys.argv[2]) if len(sys.argv) > 2 else 32  # 默认改为32 (480p)
    output_dir = sys.argv[3] if len(sys.argv) > 3 else "./downloads"
    
    downloader = VideoDownloader()
    success = await downloader.download_video(bvid, quality, output_dir)
    
    if success:
        print("下载成功!")
    else:
        print("下载失败!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())