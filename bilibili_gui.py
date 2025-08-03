import customtkinter as ctk
import asyncio
import threading
import os
import re
from pathlib import Path
from video_downloader import VideoDownloader
import tempfile
import base64
from PIL import Image, ImageTk
import io
import httpx
import random
# 设置CTk主题
ctk.set_appearance_mode("System")  # "Light", "Dark", 或 "System"
ctk.set_default_color_theme("blue")  # 蓝色主题
lucky_msg = ['祝你有美好的一天','欢迎使用👋','你好','Hello,World!','Using Video downloader']

class VideoItem:
    """视频项目类，用于存储视频信息"""
    def __init__(self, bvid, title="", cover_url="", cover_image=None):
        self.bvid = bvid
        self.title = title
        self.cover_url = cover_url
        self.cover_image = cover_image  # PIL图像对象
        self.cover_photo = None  # tkinter PhotoImage对象
        self.progress_bar = None  # 进度条控件
        self.progress_label = None  # 进度文本标签
        self.status_label = None  # 状态标签
        self.list_item_frame = None  # 列表项框架


class BilibiliVideoDownloaderGUI:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("BVideo下载")
        self.root.geometry("900x1000")
        self.root.minsize(700, 1000)  # 设置最小窗口大小
        
        # 下载器实例
        self.downloader = VideoDownloader()
        
        # 下载线程
        self.download_thread = None
        
        # 二维码图片和窗口
        self.qr_image = None
        self.qr_window = None
        self.qr_label = None
        
        # 下载列表
        self.video_list = []  # 存储VideoItem对象
        self.selected_video = None
        
        # 登录状态标签（先初始化为None）
        self.login_status_label = None
        
        # 创建UI
        self.create_widgets()
        
        # 初始化完成后尝试加载已保存的cookies
        self.load_saved_cookies()
        
    def load_saved_cookies(self):
        """加载已保存的用户cookies"""
        try:
            # 直接调用下载器的load_cookies方法
            if self.downloader.load_cookies():
                self.update_login_status("已登录")
                self.append_status("已加载已保存的用户登录信息\n")
            else:
                self.update_login_status("未登录")
                self.append_status("未找到已保存的用户信息，请点击扫码登录\n")
        except Exception as e:
            self.update_login_status("未登录")
            self.append_status(f"加载已保存的用户信息时出错: {e}\n")
            
    def create_widgets(self):
        # 主框架
        main_frame = ctk.CTkFrame(self.root)
        main_frame.pack(padx=20, pady=20, fill="both", expand=True)
        
        # 标题
        title_label = ctk.CTkLabel(main_frame, text=lucky_msg[random.randint(0,len(lucky_msg)-1)], 
                                  font=ctk.CTkFont(size=20, weight="bold"))
        title_label.pack(pady=(10, 20))
        
        # 视频链接输入框架
        url_frame = ctk.CTkFrame(main_frame)
        url_frame.pack(fill="x", padx=20, pady=5)
        
        url_label = ctk.CTkLabel(url_frame, text="视频链接:")
        url_label.pack(side="left", padx=(0, 10))
        
        self.url_entry = ctk.CTkEntry(url_frame)
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.url_entry.insert(0, "https://www.bilibili.com/video/BV1xx411c7mu")
        
        add_button = ctk.CTkButton(url_frame, text="添加到列表", 
                                  command=self.add_video_to_list, width=100)
        add_button.pack(side="right")
        
        # 下载列表框架
        list_frame = ctk.CTkFrame(main_frame)
        list_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        list_label = ctk.CTkLabel(list_frame, text="待下载列表:", 
                                 font=ctk.CTkFont(size=14, weight="bold"))
        list_label.pack(anchor="w", padx=10, pady=(10, 5))
        
        # 创建Treeview风格的列表
        list_header_frame = ctk.CTkFrame(list_frame)
        list_header_frame.pack(fill="x", padx=10, pady=(0, 5))
        
        ctk.CTkLabel(list_header_frame, text="封面", width=100).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(list_header_frame, text="视频标题", width=300).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(list_header_frame, text="BV号", width=150).pack(side="left", padx=(0, 10))
        
        # 创建可滚动的列表区域
        list_box_frame = ctk.CTkFrame(list_frame)
        list_box_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # 创建Canvas和滚动条
        self.list_canvas = ctk.CTkCanvas(list_box_frame, highlightthickness=0)
        scrollbar = ctk.CTkScrollbar(list_box_frame, orientation="vertical", command=self.list_canvas.yview)
        self.list_scrollable_frame = ctk.CTkFrame(self.list_canvas)
        
        self.list_scrollable_frame.bind(
            "<Configure>",
            lambda e: self.list_canvas.configure(
                scrollregion=self.list_canvas.bbox("all")
            )
        )
        
        self.list_canvas.create_window((0, 0), window=self.list_scrollable_frame, anchor="nw")
        self.list_canvas.configure(yscrollcommand=scrollbar.set)
        
        self.list_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 绑定鼠标滚轮事件
        self.list_canvas.bind("<MouseWheel>", self._on_mousewheel)
        
        # 分隔线
        separator = ctk.CTkFrame(main_frame, height=2, fg_color=("gray70", "gray30"))
        separator.pack(fill="x", padx=20, pady=10)
        
        # 下载设置框架
        settings_frame = ctk.CTkFrame(main_frame)
        settings_frame.pack(fill="x", padx=20, pady=10)
        
        # 质量选择框架
        quality_frame = ctk.CTkFrame(settings_frame)
        quality_frame.pack(side="left", padx=(0, 20))
        
        quality_label = ctk.CTkLabel(quality_frame, text="视频质量:")
        quality_label.pack(side="left", padx=(0, 10))
        
        self.quality_var = ctk.StringVar(value="32")
        quality_options = [
            "120: 4K超清",
            "116: 1080P60帧", 
            "74: 1080P高码率",
            "80: 1080P",
            "64: 720P",
            "32: 480P",
            "16: 360P"
        ]
        self.quality_combo = ctk.CTkComboBox(quality_frame, 
                                            values=quality_options,
                                            variable=self.quality_var,
                                            width=200)
        self.quality_combo.pack(side="left", padx=(0, 10))
        
        # 输出目录框架
        output_frame = ctk.CTkFrame(settings_frame)
        output_frame.pack(side="left", fill="x", expand=True, padx=(0, 20))
        
        output_label = ctk.CTkLabel(output_frame, text="输出目录:")
        output_label.pack(side="left", padx=(0, 10))
        
        self.output_entry = ctk.CTkEntry(output_frame)
        self.output_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.output_entry.insert(0, "./downloads")  # 默认输出目录
        
        browse_button = ctk.CTkButton(output_frame, text="浏览", 
                                     command=self.browse_directory, width=60)
        browse_button.pack(side="right")
        
        # 登录状态框架
        login_frame = ctk.CTkFrame(main_frame)
        login_frame.pack(fill="x", padx=20, pady=10)
        
        self.login_status_label = ctk.CTkLabel(login_frame, text="登录状态: 未登录")
        self.login_status_label.pack(side="left")
        
        login_button = ctk.CTkButton(login_frame, text="扫码登录", 
                                    command=self.login, width=80)
        login_button.pack(side="right")
        
        # 进度条
        self.progress_bar = ctk.CTkProgressBar(main_frame)
        self.progress_bar.pack(fill="x", padx=20, pady=10)
        self.progress_bar.set(0)
        
        # 状态文本框
        self.status_textbox = ctk.CTkTextbox(main_frame)
        self.status_textbox.pack(fill="both", expand=True, padx=20, pady=(10, 20))
        self.status_textbox.insert("0.0", "欢迎使用Bilibili视频下载器!\n\n")
        
        # 下载按钮
        self.download_button = ctk.CTkButton(main_frame, text="开始下载", 
                                            command=self.start_download,
                                            height=40, font=ctk.CTkFont(size=14))
        self.download_button.pack(fill="x", padx=20, pady=(0, 20))
        
    def _on_mousewheel(self, event):
        """处理鼠标滚轮事件"""
        self.list_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
    def add_video_to_list(self):
        """添加视频到下载列表"""
        url = self.url_entry.get().strip()
        if not url:
            self.append_status("请输入视频链接!\n")
            return
            
        # 提取BV号
        bvid = self.extract_bv_id(url)
        if not bvid:
            self.append_status("无法从链接中提取BV号，请检查链接格式!\n")
            return
            
        # 检查是否已存在
        if any(video.bvid == bvid for video in self.video_list):
            self.append_status(f"视频 {bvid} 已在下载列表中!\n")
            return
            
        # 创建视频项目并添加到列表
        video_item = VideoItem(bvid)
        self.video_list.append(video_item)
        
        # 在后台线程中获取视频信息
        thread = threading.Thread(target=self.fetch_video_info, args=(video_item,))
        thread.daemon = True
        thread.start()
        
        self.append_status(f"已添加视频 {bvid} 到下载列表，正在获取详细信息...\n")
        
    def extract_bv_id(self, url):
        """从URL中提取BV号"""
        # 匹配BV号的正则表达式
        patterns = [
            r"BV[0-9A-Za-z]{10}",  # 标准BV号格式
            r"bilibili\.com/video/(BV[0-9A-Za-z]{10})",  # URL中的BV号
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(0) if match.group(0).startswith("BV") else match.group(1)
                
        return None
        
    def fetch_video_info(self, video_item):
        """获取视频详细信息"""
        try:
            # 创建事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._fetch_video_info_async(video_item))
            loop.close()
        except Exception as e:
            self.append_status(f"获取视频 {video_item.bvid} 信息失败: {str(e)}\n")
    
    async def _fetch_video_info_async(self, video_item):
        """异步获取视频详细信息"""
        try:
            # 使用BilibiliClient获取视频信息
            from backend.bilibili.client import BilibiliClient
            
            client = BilibiliClient()
            if self.downloader.cookies:
                client.set_cookies(self.downloader.cookies)
                await client.get_wbi_keys()
            
            video_info = await client.get_video_info(bvid=video_item.bvid)
            
            if video_info and video_info.get('code') == 0:
                data = video_info['data']
                video_item.title = data['title']
                video_item.cover_url = data['pic']
                
                # 下载封面图片
                async with httpx.AsyncClient() as httpx_client:
                    response = await httpx_client.get(video_item.cover_url)
                    if response.status_code == 200:
                        image_data = response.content
                        video_item.cover_image = Image.open(io.BytesIO(image_data))
                        # 调整图片大小
                        video_item.cover_image = video_item.cover_image.resize((80, 60), Image.LANCZOS)
                        # 转换为tkinter可用的格式
                        video_item.cover_photo = ImageTk.PhotoImage(video_item.cover_image)
                
                # 更新UI
                self.root.after(0, self.update_video_list_ui)
                self.append_status(f"已获取视频 {video_item.bvid} 的详细信息\n")
            else:
                self.append_status(f"获取视频 {video_item.bvid} 信息失败: {video_info.get('message', '未知错误')}\n")
                # 更新UI
                self.root.after(0, self.update_video_list_ui)
        except Exception as e:
            self.append_status(f"获取视频 {video_item.bvid} 信息时出错: {str(e)}\n")
            # 更新UI
            self.root.after(0, self.update_video_list_ui)
    
    def update_video_list_ui(self):
        """更新视频列表UI"""
        # 清空当前列表显示
        for widget in self.list_scrollable_frame.winfo_children():
            widget.destroy()
            
        # 为整个列表添加统一的左右边距
        list_padding = ctk.CTkFrame(self.list_scrollable_frame, fg_color="transparent")
        list_padding.pack(fill="both", expand=True, padx=0, pady=0)
        
        # 添加视频项到列表
        for i, video in enumerate(self.video_list):
            # 视频项主框架，使用与列表相同宽度并添加内边距
            item_frame = ctk.CTkFrame(list_padding, corner_radius=6)
            item_frame.pack(fill="x", padx=5, pady=5)
            video.list_item_frame = item_frame  # 保存框架引用
            
            # 内容框架，使用左右内边距确保内容不贴边
            content_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
            content_frame.pack(fill="both", expand=True, padx=10, pady=10)
            
            # 封面图片区域
            cover_frame = ctk.CTkFrame(content_frame, width=80, height=60, fg_color="transparent")
            cover_frame.pack(side="left", padx=(0, 15), pady=0)
            cover_frame.pack_propagate(False)  # 保持固定大小
            
            if video.cover_photo:
                cover_label = ctk.CTkLabel(cover_frame, image=video.cover_photo, text="")
                cover_label.pack(expand=True)
            else:
                cover_label = ctk.CTkLabel(cover_frame, text="无封面", font=("Arial", 8))
                cover_label.pack(expand=True)
            
            # 中间信息区域
            info_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
            info_frame.pack(side="left", fill="x", expand=True, pady=0)
            
            # 标题
            title_text = video.title if video.title else "获取中..."
            title_label = ctk.CTkLabel(info_frame, text=title_text, anchor="w", wraplength=250)
            title_label.pack(fill="x")
            
            # BV号
            bvid_label = ctk.CTkLabel(info_frame, text=f"BV号: {video.bvid}", anchor="w", 
                                     font=ctk.CTkFont(size=12))
            bvid_label.pack(fill="x", pady=(3, 0))
            
            # 右侧操作区域
            action_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
            action_frame.pack(side="right", padx=(10, 0), pady=0)
            
            # 删除按钮
            remove_button = ctk.CTkButton(
                action_frame, 
                text="删除",
                width=60,
                height=25,
                command=lambda v=video: self.remove_video_from_list(v)
            )
            remove_button.pack()
            
            # 进度信息区域
            progress_container = ctk.CTkFrame(item_frame, fg_color="transparent")
            progress_container.pack(fill="x", padx=10, pady=(0, 10))
            
            # 进度条和状态信息
            progress_frame = ctk.CTkFrame(progress_container, fg_color="transparent")
            progress_frame.pack(fill="x", expand=True)
            
            # 进度条
            progress_bar = ctk.CTkProgressBar(progress_frame)
            progress_bar.pack(side="left", fill="x", expand=True)
            progress_bar.set(0)
            video.progress_bar = progress_bar
            
            # 进度百分比
            progress_label = ctk.CTkLabel(progress_frame, text="0%", width=40)
            progress_label.pack(side="left", padx=(10, 5))
            video.progress_label = progress_label
            
            # 状态标签
            status_label = ctk.CTkLabel(progress_frame, text="等待下载")
            status_label.pack(side="right")
            video.status_label = status_label
            
        # 更新滚动区域
        self.list_canvas.update_idletasks()
        self.list_canvas.configure(scrollregion=self.list_canvas.bbox("all"))
        
    def remove_video_from_list(self, video_item):
        """从下载列表中删除视频"""
        if video_item in self.video_list:
            self.video_list.remove(video_item)
            self.update_video_list_ui()
            self.append_status(f"已从下载列表中删除视频 {video_item.bvid}\n")
        
    def browse_directory(self):
        """浏览并选择输出目录"""
        from tkinter import filedialog
        directory = filedialog.askdirectory()
        if directory:
            self.output_entry.delete(0, "end")
            self.output_entry.insert(0, directory)
            
    def login(self):
        """执行登录操作"""
        def login_task():
            self.append_status("正在启动登录流程...\n")
            try:
                # 使用自定义的二维码登录方法
                self.qr_login_gui()
            except Exception as e:
                self.append_status(f"登录过程中出现错误: {str(e)}\n")
                self.update_login_status("登录失败")
                
        login_thread = threading.Thread(target=login_task)
        login_thread.daemon = True
        login_thread.start()
        
    def qr_login_gui(self):
        """在GUI中执行二维码登录"""
        try:
            # 创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self._qr_login_gui_async())
            loop.close()
            
            if result:
                self.append_status("登录成功!\n")
                self.update_login_status("已登录")
            else:
                self.append_status("登录失败!\n")
                self.update_login_status("登录失败")
        except Exception as e:
            self.append_status(f"登录过程中出现错误: {str(e)}\n")
            self.update_login_status("登录失败")
    
    async def _qr_login_gui_async(self):
        """异步执行二维码登录并在GUI中显示二维码"""
        try:
            from backend.bilibili.auth import BilibiliAuth
            
            async with BilibiliAuth() as auth:
                # 获取二维码
                self.append_status("正在生成二维码...\n")
                qr_data = await auth.login_with_qr()
                
                if qr_data['status'] != 'qr_ready':
                    self.append_status(f"获取二维码失败: {qr_data['message']}\n")
                    return False
                
                # 显示二维码到GUI
                qr_image_data = qr_data['qr_image']
                qrcode_key = qr_data['qrcode_key']
                
                # 解码base64数据
                header, encoded = qr_image_data.split(",", 1)
                qr_bytes = base64.b64decode(encoded)
                
                # 创建PIL图像
                image = Image.open(io.BytesIO(qr_bytes))
                
                # 在GUI中显示二维码
                self.show_qr_code(image)
                
                self.append_status("请使用Bilibili手机客户端扫描二维码\n")
                
                # 轮询检查扫码状态
                max_attempts = 100  # 最大尝试次数
                attempt = 0
                
                while attempt < max_attempts:
                    status = await auth.check_qr_status(qrcode_key)
                    
                    if status['status'] == 'success':
                        self.append_status("登录成功!\n")
                        self.close_qr_window()  # 关闭二维码窗口
                        
                        # 保存cookies
                        cookies = status['cookies']
                        # 获取用户信息
                        user_info = await self._get_user_info_with_cookies(cookies)
                        user_id = user_info.get('mid', 'unknown_user')
                        
                        # 保存到cookie管理器
                        from backend.utils.cookie_manager import cookie_manager
                        cookie_manager.save_cookies(user_id, cookies, user_info)
                        
                        # 更新当前实例的cookies
                        self.downloader.cookies = cookies
                        self.append_status(f"已保存用户: {user_info.get('uname', user_id)}\n")
                        return True
                        
                    elif status['status'] == 'waiting':
                        self.append_status("等待扫码...\n", replace_last=True)
                    elif status['status'] == 'scanned':
                        self.append_status("已扫码，等待确认...\n", replace_last=True)
                    elif status['status'] == 'expired':
                        self.append_status("二维码已过期，请重新登录\n")
                        self.close_qr_window()  # 关闭二维码窗口
                        return False
                    else:
                        self.append_status(f"登录出错: {status['message']}\n")
                        self.close_qr_window()  # 关闭二维码窗口
                        return False
                    
                    attempt += 1
                    await asyncio.sleep(3)  # 每3秒检查一次
                
                self.append_status("登录超时，请重新登录\n")
                self.close_qr_window()  # 关闭二维码窗口
                return False
        except Exception as e:
            self.append_status(f"扫码登录异常: {str(e)}\n")
            self.close_qr_window()  # 关闭二维码窗口
            return False
    
    async def _get_user_info_with_cookies(self, cookies: dict):
        """使用cookies获取用户信息"""
        try:
            from backend.bilibili.client import BilibiliClient
            client = BilibiliClient()
            client.set_cookies(cookies)
            await client.get_wbi_keys()
            user_info = await client.get_user_info()
            return user_info
        except Exception as e:
            self.append_status(f"获取用户信息失败: {str(e)}\n")
            return {}
    
    def show_qr_code(self, image: Image.Image):
        """在新窗口中显示二维码"""
        # 如果二维码窗口已经存在，先关闭它
        self.close_qr_window()
        
        # 创建新窗口
        self.qr_window = ctk.CTkToplevel(self.root)
        self.qr_window.title("扫码登录")
        self.qr_window.geometry("300x350")
        self.qr_window.resizable(False, False)
        
        # 确保窗口在最前面
        self.qr_window.lift()
        self.qr_window.focus_force()
        
        # 添加说明文字
        instruction_label = ctk.CTkLabel(
            self.qr_window, 
            text="请使用Bilibili手机客户端扫描二维码",
            wraplength=250
        )
        instruction_label.pack(pady=(20, 10))
        
        # 调整图像大小
        image = image.resize((256, 256), Image.LANCZOS)
        
        # 转换为CTk可以显示的格式
        self.qr_image = ImageTk.PhotoImage(image)
        
        # 创建显示二维码的标签
        self.qr_label = ctk.CTkLabel(self.qr_window, image=self.qr_image, text="")
        self.qr_label.pack(pady=10)
        
        # 添加关闭按钮
        close_button = ctk.CTkButton(
            self.qr_window, 
            text="关闭", 
            command=self.close_qr_window
        )
        close_button.pack(pady=10)
        
        # 确保窗口关闭时清理资源
        self.qr_window.protocol("WM_DELETE_WINDOW", self.close_qr_window)
    
    def close_qr_window(self):
        """关闭二维码窗口"""
        if self.qr_window and self.qr_window.winfo_exists():
            try:
                self.qr_window.destroy()
            except:
                pass
        self.qr_window = None
        self.qr_image = None
        self.qr_label = None
    
    def update_login_status(self, status):
        """更新登录状态显示"""
        # 检查标签是否存在
        if self.login_status_label is not None and self.login_status_label.winfo_exists():
            self.login_status_label.configure(text=f"登录状态: {status}")
        
    def append_status(self, text, replace_last=False):
        """向状态文本框添加文本"""
        if replace_last:
            # 删除最后一行并替换
            self.status_textbox.delete("end-1c linestart", "end-1c")
        
        self.status_textbox.insert("end", text)
        self.status_textbox.see("end")
        self.root.update()
        
    def start_download(self):
        """开始下载视频"""
        if not self.video_list:
            self.append_status("请先添加视频到下载列表!\n")
            return
            
        # 解析选中的质量
        quality_text = self.quality_var.get()
        quality = int(quality_text.split(":")[0])
        
        output_dir = self.output_entry.get().strip()
        if not output_dir:
            output_dir = "./downloads"
            
        # 禁用下载按钮
        self.download_button.configure(state="disabled", text="下载中...")
        
        # 在后台线程中执行下载
        self.download_thread = threading.Thread(
            target=self.download_videos, 
            args=(quality, output_dir)
        )
        self.download_thread.daemon = True
        self.download_thread.start()
        
    def download_videos(self, quality, output_dir):
        """在后台线程中下载所有视频（支持多线程）"""
        try:
            total_videos = len(self.video_list)
            self.append_status(f"开始下载 {total_videos} 个视频...\n")
            
            # 使用线程池并发下载多个视频
            import concurrent.futures
            max_workers = min(3, total_videos)  # 最多同时下载3个视频
            
            def download_single_video(video_item):
                """下载单个视频"""
                # 更新UI状态
                self.root.after(0, lambda: self.update_video_status(video_item, "准备下载...", 0))
                
                # 使用 asyncio 运行下载任务
                async def download_task():
                    # 确保客户端已初始化
                    init_result = await self.downloader.init_client()
                    if not init_result:
                        self.root.after(0, lambda: self.update_video_status(video_item, "初始化失败", 0))
                        return False
                    
                    # 定义进度回调函数
                    def progress_callback(status, progress):
                        self.root.after(0, lambda: self.update_video_status(video_item, status, progress))
                    
                    # 下载视频
                    success = await self.downloader.download_video(
                        video_item.bvid, quality, output_dir, progress_callback
                    )
                    return success
                
                try:
                    result = asyncio.run(download_task())
                    return video_item, result
                except Exception as e:
                    self.root.after(0, lambda: self.update_video_status(video_item, f"错误: {str(e)}", 0))
                    return video_item, False
            
            # 使用线程池执行下载任务
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交所有下载任务
                future_to_video = {
                    executor.submit(download_single_video, video): video 
                    for video in self.video_list
                }
                
                # 等待所有任务完成
                success_count = 0
                for future in concurrent.futures.as_completed(future_to_video):
                    video_item, success = future.result()
                    if success:
                        success_count += 1
                        self.root.after(0, lambda v=video_item: self.update_video_status(v, "下载完成", 1.0))
                    else:
                        self.root.after(0, lambda v=video_item: self.update_video_status(v, "下载失败", 0))
                
                # 更新总体状态
                self.root.after(0, lambda: self.append_status(
                    f"下载完成: {success_count}/{total_videos} 个视频下载成功\n"
                ))
                
        except Exception as e:
            self.append_status(f"下载过程中出现错误: {str(e)}\n")
        finally:
            # 重新启用下载按钮
            def reset_button():
                if self.download_button.winfo_exists():
                    self.download_button.configure(state="normal", text="开始下载")
            
            self.root.after(0, reset_button)
            
    def update_video_status(self, video_item, status, progress):
        """更新视频下载状态和进度"""
        try:
            if video_item.progress_bar and video_item.progress_bar.winfo_exists():
                video_item.progress_bar.set(progress)
                
            if video_item.progress_label and video_item.progress_label.winfo_exists():
                if progress >= 1.0:
                    video_item.progress_label.configure(text="100%")
                else:
                    video_item.progress_label.configure(text=f"{int(progress * 100)}%")
                    
            if video_item.status_label and video_item.status_label.winfo_exists():
                video_item.status_label.configure(text=status)
        except Exception as e:
            pass  # 忽略UI更新错误
    
    def run(self):
        """运行GUI应用"""
        self.root.mainloop()


if __name__ == "__main__":
    app = BilibiliVideoDownloaderGUI()
    app.run()