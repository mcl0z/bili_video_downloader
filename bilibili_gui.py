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
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

# 欢迎消息
lucky_msg = ['祝你有美好的一天', '欢迎使用👋', '你好', 'Hello,World!', 'Using Video downloader']

class VideoItem:
    """视频项目类，用于存储视频信息"""
    def __init__(self, bvid, title="", cover_url="", cover_image=None):
        self.bvid = bvid
        self.title = title
        self.cover_url = cover_url
        self.cover_image = cover_image
        self.cover_photo = None
        self.progress_bar = None
        self.progress_label = None
        self.status_label = None
        self.list_item_frame = None


class BilibiliVideoDownloaderGUI:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("BVideo下载器")
        self.root.geometry("1100x800")
        self.root.minsize(900, 600)
        
        # 设置应用图标和标题栏样式
        self.root.wm_attributes("-alpha", 0.98)
        
        # 下载器实例
        self.downloader = VideoDownloader()
        
        # 下载线程
        self.download_thread = None
        
        # 二维码相关
        self.qr_image = None
        self.qr_window = None
        self.qr_label = None
        
        # 下载列表
        self.video_list = []
        self.selected_video = None
        
        # 登录状态标签
        self.login_status_label = None
        
        # 创建UI
        self.create_widgets()
        
        # 初始化完成后尝试加载已保存的cookies
        self.load_saved_cookies()
        
    def load_saved_cookies(self):
        """加载已保存的用户cookies"""
        try:
            if self.downloader.load_cookies():
                self.update_login_status("已登录", True)
                self.append_status("✅ 已加载已保存的用户登录信息")
            else:
                self.update_login_status("未登录", False)
                self.append_status("ℹ️ 未找到已保存的用户信息，请点击扫码登录")
        except Exception as e:
            self.update_login_status("未登录", False)
            self.append_status(f"❌ 加载已保存的用户信息时出错: {e}")
            
    def create_widgets(self):
        # 创建主容器，使用网格布局
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        
        # 主滚动框架
        main_scroll = ctk.CTkScrollableFrame(self.root, corner_radius=0)
        main_scroll.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        main_scroll.grid_columnconfigure(0, weight=1)
        
        # === 顶部标题区域 ===
        self.create_header_section(main_scroll)
        
        # === 输入区域 ===
        self.create_input_section(main_scroll)
        
        # === 设置区域 ===
        self.create_settings_section(main_scroll)
        
        # === 视频列表区域 ===
        self.create_video_list_section(main_scroll)
        
        # === 状态和控制区域 ===
        self.create_status_section(main_scroll)
        
    def create_header_section(self, parent):
        """创建顶部标题区域"""
        header_frame = ctk.CTkFrame(parent, height=120, corner_radius=15)
        header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        header_frame.grid_columnconfigure(1, weight=1)
        header_frame.grid_propagate(False)
        
        # 应用图标/Logo区域
        icon_frame = ctk.CTkFrame(header_frame, width=80, height=80, corner_radius=40)
        icon_frame.grid(row=0, column=0, padx=20, pady=20)
        icon_frame.grid_propagate(False)
        
        icon_label = ctk.CTkLabel(icon_frame, text="📺", font=ctk.CTkFont(size=32))
        icon_label.place(relx=0.5, rely=0.5, anchor="center")
        
        # 标题和欢迎信息
        title_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_frame.grid(row=0, column=1, sticky="ew", padx=20, pady=20)
        
        title_label = ctk.CTkLabel(
            title_frame, 
            text="BVideo 下载器", 
            font=ctk.CTkFont(size=28, weight="bold")
        )
        title_label.pack(anchor="w")
        
        subtitle_label = ctk.CTkLabel(
            title_frame,
            text=lucky_msg[random.randint(0, len(lucky_msg)-1)],
            font=ctk.CTkFont(size=14),
            text_color=("gray60", "gray40")
        )
        subtitle_label.pack(anchor="w", pady=(5, 0))
        
        # 登录状态指示器
        status_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        status_frame.grid(row=0, column=2, padx=20, pady=20)
        
        self.login_status_indicator = ctk.CTkFrame(status_frame, width=12, height=12, corner_radius=6)
        self.login_status_indicator.pack(side="top", pady=(0, 5))
        self.login_status_indicator.grid_propagate(False)
        
        self.login_status_label = ctk.CTkLabel(
            status_frame, 
            text="未登录", 
            font=ctk.CTkFont(size=12)
        )
        self.login_status_label.pack()
        
        self.login_button = ctk.CTkButton(
            status_frame,
            text="🔑 扫码登录",
            command=self.login,
            width=100,
            height=32,
            corner_radius=16,
            font=ctk.CTkFont(size=12)
        )
        self.login_button.pack(pady=(10, 0))
        
    def create_input_section(self, parent):
        """创建输入区域"""
        input_frame = ctk.CTkFrame(parent, corner_radius=15)
        input_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=10)
        input_frame.grid_columnconfigure(1, weight=1)
        
        # 输入标签
        input_label = ctk.CTkLabel(
            input_frame, 
            text="🔗 视频链接:", 
            font=ctk.CTkFont(size=16, weight="bold")
        )
        input_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        
        # 输入框容器
        entry_container = ctk.CTkFrame(input_frame, fg_color="transparent")
        entry_container.grid(row=1, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 20))
        entry_container.grid_columnconfigure(0, weight=1)
        
        # 输入框
        self.url_entry = ctk.CTkEntry(
            entry_container,
            placeholder_text="请输入Bilibili视频链接，例如: https://www.bilibili.com/video/BV1xx411c7mu",
            height=40,
            font=ctk.CTkFont(size=14),
            corner_radius=20
        )
        self.url_entry.grid(row=0, column=0, sticky="ew", padx=(0, 15))
        self.url_entry.insert(0, "https://www.bilibili.com/video/BV1xx411c7mu")
        
        # 添加按钮
        add_button = ctk.CTkButton(
            entry_container,
            text="➕ 添加到列表",
            command=self.add_video_to_list,
            width=140,
            height=40,
            corner_radius=20,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        add_button.grid(row=0, column=1)
        
    def create_settings_section(self, parent):
        """创建设置区域"""
        settings_frame = ctk.CTkFrame(parent, corner_radius=15)
        settings_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=10)
        settings_frame.grid_columnconfigure((0, 1), weight=1)
        
        # 设置标题
        settings_label = ctk.CTkLabel(
            settings_frame, 
            text="⚙️ 下载设置", 
            font=ctk.CTkFont(size=16, weight="bold")
        )
        settings_label.grid(row=0, column=0, columnspan=2, padx=20, pady=(20, 15), sticky="w")
        
        # 质量设置
        quality_container = ctk.CTkFrame(settings_frame, fg_color="transparent")
        quality_container.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 20))
        
        quality_label = ctk.CTkLabel(
            quality_container, 
            text="🎬 视频质量:", 
            font=ctk.CTkFont(size=14)
        )
        quality_label.pack(anchor="w", pady=(0, 8))
        
        self.quality_var = ctk.StringVar(value="80: 1080P")
        quality_options = [
            "120: 4K超清", "116: 1080P60帧", "74: 1080P高码率",
            "80: 1080P", "64: 720P", "32: 480P", "16: 360P"
        ]
        self.quality_combo = ctk.CTkComboBox(
            quality_container,
            values=quality_options,
            variable=self.quality_var,
            width=200,
            height=35,
            corner_radius=17,
            font=ctk.CTkFont(size=13)
        )
        self.quality_combo.pack(anchor="w")
        
        # 输出目录设置
        output_container = ctk.CTkFrame(settings_frame, fg_color="transparent")
        output_container.grid(row=1, column=1, sticky="ew", padx=20, pady=(0, 20))
        
        output_label = ctk.CTkLabel(
            output_container, 
            text="📁 输出目录:", 
            font=ctk.CTkFont(size=14)
        )
        output_label.pack(anchor="w", pady=(0, 8))
        
        output_entry_frame = ctk.CTkFrame(output_container, fg_color="transparent")
        output_entry_frame.pack(fill="x")
        output_entry_frame.grid_columnconfigure(0, weight=1)
        
        self.output_entry = ctk.CTkEntry(
            output_entry_frame,
            placeholder_text="选择下载目录",
            height=35,
            corner_radius=17,
            font=ctk.CTkFont(size=13)
        )
        self.output_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.output_entry.insert(0, "./downloads")
        
        browse_button = ctk.CTkButton(
            output_entry_frame,
            text="📂",
            command=self.browse_directory,
            width=40,
            height=35,
            corner_radius=17
        )
        browse_button.grid(row=0, column=1)
        
    def create_video_list_section(self, parent):
        """创建视频列表区域"""
        list_frame = ctk.CTkFrame(parent, corner_radius=15)
        list_frame.grid(row=3, column=0, sticky="ew", padx=20, pady=10)
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(1, weight=1)
        
        # 列表标题
        list_header = ctk.CTkFrame(list_frame, fg_color="transparent")
        list_header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        list_header.grid_columnconfigure(1, weight=1)
        
        list_title = ctk.CTkLabel(
            list_header, 
            text="📋 待下载列表", 
            font=ctk.CTkFont(size=16, weight="bold")
        )
        list_title.grid(row=0, column=0, sticky="w")
        
        # 列表统计信息
        self.list_stats_label = ctk.CTkLabel(
            list_header,
            text="共 0 个视频",
            font=ctk.CTkFont(size=12),
            text_color=("gray60", "gray40")
        )
        self.list_stats_label.grid(row=0, column=1, sticky="e")
        
        # 清空列表按钮
        clear_button = ctk.CTkButton(
            list_header,
            text="🗑️ 清空",
            command=self.clear_video_list,
            width=80,
            height=28,
            corner_radius=14,
            font=ctk.CTkFont(size=12)
        )
        clear_button.grid(row=0, column=2, padx=(10, 0))
        
        # 创建滚动列表区域
        self.list_scroll_frame = ctk.CTkScrollableFrame(
            list_frame, 
            height=300,
            corner_radius=10
        )
        self.list_scroll_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 20))
        self.list_scroll_frame.grid_columnconfigure(0, weight=1)
        
        # 空列表提示
        self.empty_list_label = ctk.CTkLabel(
            self.list_scroll_frame,
            text="📝 暂无视频，请添加视频链接",
            font=ctk.CTkFont(size=14),
            text_color=("gray50", "gray50")
        )
        self.empty_list_label.grid(row=0, column=0, pady=50)
        
    def create_status_section(self, parent):
        """创建状态和控制区域"""
        # 状态区域
        status_frame = ctk.CTkFrame(parent, corner_radius=15)
        status_frame.grid(row=4, column=0, sticky="ew", padx=20, pady=10)
        status_frame.grid_columnconfigure(0, weight=1)
        
        # 状态标题
        status_label = ctk.CTkLabel(
            status_frame, 
            text="📊 运行状态", 
            font=ctk.CTkFont(size=16, weight="bold")
        )
        status_label.grid(row=0, column=0, sticky="w", padx=20, pady=(20, 10))
        
        # 总体进度条
        progress_container = ctk.CTkFrame(status_frame, fg_color="transparent")
        progress_container.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 10))
        progress_container.grid_columnconfigure(0, weight=1)
        
        self.overall_progress_label = ctk.CTkLabel(
            progress_container,
            text="总体进度: 0/0",
            font=ctk.CTkFont(size=12)
        )
        self.overall_progress_label.grid(row=0, column=0, sticky="w", pady=(0, 5))
        
        self.overall_progress_bar = ctk.CTkProgressBar(
            progress_container,
            height=8,
            corner_radius=4
        )
        self.overall_progress_bar.grid(row=1, column=0, sticky="ew")
        self.overall_progress_bar.set(0)
        
        # 状态文本框
        self.status_textbox = ctk.CTkTextbox(
            status_frame,
            height=150,
            corner_radius=10,
            font=ctk.CTkFont(family="Consolas", size=12)
        )
        self.status_textbox.grid(row=2, column=0, sticky="ew", padx=20, pady=(10, 20))
        self.status_textbox.insert("0.0", "🎉 欢迎使用Bilibili视频下载器!\n")
        
        # 下载控制区域
        control_frame = ctk.CTkFrame(parent, corner_radius=15)
        control_frame.grid(row=5, column=0, sticky="ew", padx=20, pady=(10, 20))
        control_frame.grid_columnconfigure(0, weight=1)
        
        # 下载按钮
        self.download_button = ctk.CTkButton(
            control_frame,
            text="🚀 开始下载",
            command=self.start_download,
            height=50,
            corner_radius=25,
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.download_button.grid(row=0, column=0, sticky="ew", padx=20, pady=20)
        
    def clear_video_list(self):
        """清空视频列表"""
        if not self.video_list:
            return
            
        self.video_list.clear()
        self.update_video_list_ui()
        self.append_status("🗑️ 已清空视频列表")
        
    def add_video_to_list(self):
        """添加视频到下载列表"""
        url = self.url_entry.get().strip()
        if not url:
            self.append_status("❌ 请输入视频链接!")
            return
            
        # 提取BV号
        bvid = self.extract_bv_id(url)
        if not bvid:
            self.append_status("❌ 无法从链接中提取BV号，请检查链接格式!")
            return
            
        # 检查是否已存在
        if any(video.bvid == bvid for video in self.video_list):
            self.append_status(f"⚠️ 视频 {bvid} 已在下载列表中!")
            return
            
        # 创建视频项目并添加到列表
        video_item = VideoItem(bvid)
        self.video_list.append(video_item)
        
        # 在后台线程中获取视频信息
        thread = threading.Thread(target=self.fetch_video_info, args=(video_item,))
        thread.daemon = True
        thread.start()
        
        # 清空输入框
        self.url_entry.delete(0, "end")
        
        self.append_status(f"➕ 已添加视频 {bvid} 到下载列表，正在获取详细信息...")
        self.update_video_list_ui()
        
    def extract_bv_id(self, url):
        """从URL中提取BV号"""
        patterns = [
            r"BV[0-9A-Za-z]{10}",
            r"bilibili\.com/video/(BV[0-9A-Za-z]{10})",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(0) if match.group(0).startswith("BV") else match.group(1)
                
        return None
        
    def fetch_video_info(self, video_item):
        """获取视频详细信息"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._fetch_video_info_async(video_item))
            loop.close()
        except Exception as e:
            self.append_status(f"❌ 获取视频 {video_item.bvid} 信息失败: {str(e)}")
    
    async def _fetch_video_info_async(self, video_item):
        """异步获取视频详细信息"""
        try:
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
                        video_item.cover_image = video_item.cover_image.resize((100, 75), Image.LANCZOS)
                        video_item.cover_photo = ImageTk.PhotoImage(video_item.cover_image)
                
                self.root.after(0, self.update_video_list_ui)
                self.append_status(f"✅ 已获取视频 {video_item.bvid} 的详细信息")
            else:
                self.append_status(f"❌ 获取视频 {video_item.bvid} 信息失败: {video_info.get('message', '未知错误')}")
                self.root.after(0, self.update_video_list_ui)
        except Exception as e:
            self.append_status(f"❌ 获取视频 {video_item.bvid} 信息时出错: {str(e)}")
            self.root.after(0, self.update_video_list_ui)
    
    def update_video_list_ui(self):
        """更新视频列表UI"""
        # 清空当前列表显示
        for widget in self.list_scroll_frame.winfo_children():
            widget.destroy()
            
        # 更新统计信息
        self.list_stats_label.configure(text=f"共 {len(self.video_list)} 个视频")
        
        if not self.video_list:
            # 显示空列表提示
            self.empty_list_label = ctk.CTkLabel(
                self.list_scroll_frame,
                text="📝 暂无视频，请添加视频链接",
                font=ctk.CTkFont(size=14),
                text_color=("gray50", "gray50")
            )
            self.empty_list_label.grid(row=0, column=0, pady=50)
            return
        
        # 添加视频项到列表
        for i, video in enumerate(self.video_list):
            # 创建视频卡片
            card = ctk.CTkFrame(self.list_scroll_frame, corner_radius=10)
            card.grid(row=i, column=0, sticky="ew", padx=10, pady=8)
            card.grid_columnconfigure(1, weight=1)
            video.list_item_frame = card
            
            # 封面区域
            cover_frame = ctk.CTkFrame(card, width=100, height=75, corner_radius=8)
            cover_frame.grid(row=0, column=0, rowspan=2, padx=15, pady=15)
            cover_frame.grid_propagate(False)
            
            if video.cover_photo:
                cover_label = ctk.CTkLabel(cover_frame, image=video.cover_photo, text="")
                cover_label.place(relx=0.5, rely=0.5, anchor="center")
            else:
                cover_label = ctk.CTkLabel(cover_frame, text="📷\n加载中", font=ctk.CTkFont(size=10))
                cover_label.place(relx=0.5, rely=0.5, anchor="center")
            
            # 信息区域
            info_frame = ctk.CTkFrame(card, fg_color="transparent")
            info_frame.grid(row=0, column=1, sticky="ew", padx=(0, 15), pady=(15, 5))
            info_frame.grid_columnconfigure(0, weight=1)
            
            # 标题
            title_text = video.title if video.title else "获取中..."
            title_label = ctk.CTkLabel(
                info_frame, 
                text=title_text, 
                anchor="w", 
                wraplength=400,
                font=ctk.CTkFont(size=14, weight="bold")
            )
            title_label.grid(row=0, column=0, sticky="ew")
            
            # BV号和操作按钮
            bv_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
            bv_frame.grid(row=1, column=0, sticky="ew", pady=(5, 0))
            bv_frame.grid_columnconfigure(0, weight=1)
            
            bvid_label = ctk.CTkLabel(
                bv_frame, 
                text=f"🎬 {video.bvid}", 
                anchor="w", 
                font=ctk.CTkFont(size=12),
                text_color=("gray60", "gray40")
            )
            bvid_label.grid(row=0, column=0, sticky="w")
            
            remove_button = ctk.CTkButton(
                bv_frame,
                text="🗑️",
                width=30,
                height=25,
                corner_radius=12,
                command=lambda v=video: self.remove_video_from_list(v),
                font=ctk.CTkFont(size=12)
            )
            remove_button.grid(row=0, column=1, sticky="e")
            
            # 进度区域
            progress_frame = ctk.CTkFrame(card, fg_color="transparent")
            progress_frame.grid(row=1, column=1, sticky="ew", padx=(0, 15), pady=(5, 15))
            progress_frame.grid_columnconfigure(0, weight=1)
            
            # 进度条
            progress_bar = ctk.CTkProgressBar(progress_frame, height=6, corner_radius=3)
            progress_bar.grid(row=0, column=0, sticky="ew", padx=(0, 10))
            progress_bar.set(0)
            video.progress_bar = progress_bar
            
            # 进度信息
            progress_info_frame = ctk.CTkFrame(progress_frame, fg_color="transparent")
            progress_info_frame.grid(row=1, column=0, sticky="ew", pady=(5, 0))
            progress_info_frame.grid_columnconfigure(1, weight=1)
            
            progress_label = ctk.CTkLabel(
                progress_info_frame, 
                text="0%", 
                font=ctk.CTkFont(size=11),
                width=40
            )
            progress_label.grid(row=0, column=0, sticky="w")
            video.progress_label = progress_label
            
            status_label = ctk.CTkLabel(
                progress_info_frame, 
                text="等待下载",
                font=ctk.CTkFont(size=11),
                text_color=("gray60", "gray40")
            )
            status_label.grid(row=0, column=2, sticky="e")
            video.status_label = status_label
            
    def remove_video_from_list(self, video_item):
        """从下载列表中删除视频"""
        if video_item in self.video_list:
            self.video_list.remove(video_item)
            self.update_video_list_ui()
            self.append_status(f"🗑️ 已从下载列表中删除视频 {video_item.bvid}")
        
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
            self.append_status("🔑 正在启动登录流程...")
            try:
                self.qr_login_gui()
            except Exception as e:
                self.append_status(f"❌ 登录过程中出现错误: {str(e)}")
                self.update_login_status("登录失败", False)
                
        login_thread = threading.Thread(target=login_task)
        login_thread.daemon = True
        login_thread.start()
        
    def qr_login_gui(self):
        """在GUI中执行二维码登录"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self._qr_login_gui_async())
            loop.close()
            
            if result:
                self.append_status("✅ 登录成功!")
                self.update_login_status("已登录", True)
            else:
                self.append_status("❌ 登录失败!")
                self.update_login_status("登录失败", False)
        except Exception as e:
            self.append_status(f"❌ 登录过程中出现错误: {str(e)}")
            self.update_login_status("登录失败", False)
    
    async def _qr_login_gui_async(self):
        """异步执行二维码登录并在GUI中显示二维码"""
        try:
            from backend.bilibili.auth import BilibiliAuth
            
            async with BilibiliAuth() as auth:
                self.append_status("📱 正在生成二维码...")
                qr_data = await auth.login_with_qr()
                
                if qr_data['status'] != 'qr_ready':
                    self.append_status(f"❌ 获取二维码失败: {qr_data['message']}")
                    return False
                
                # 显示二维码到GUI
                qr_image_data = qr_data['qr_image']
                qrcode_key = qr_data['qrcode_key']
                
                header, encoded = qr_image_data.split(",", 1)
                qr_bytes = base64.b64decode(encoded)
                image = Image.open(io.BytesIO(qr_bytes))
                
                self.show_qr_code(image)
                self.append_status("📱 请使用Bilibili手机客户端扫描二维码")
                
                # 轮询检查扫码状态
                max_attempts = 100
                attempt = 0
                
                while attempt < max_attempts:
                    status = await auth.check_qr_status(qrcode_key)
                    
                    if status['status'] == 'success':
                        self.append_status("✅ 登录成功!")
                        self.close_qr_window()
                        
                        cookies = status['cookies']
                        user_info = await self._get_user_info_with_cookies(cookies)
                        user_id = user_info.get('mid', 'unknown_user')
                        
                        from backend.utils.cookie_manager import cookie_manager
                        cookie_manager.save_cookies(user_id, cookies, user_info)
                        
                        self.downloader.cookies = cookies
                        self.append_status(f"👤 已保存用户: {user_info.get('uname', user_id)}")
                        return True
                        
                    elif status['status'] == 'waiting':
                        self.append_status("⏳ 等待扫码...", replace_last=True)
                    elif status['status'] == 'scanned':
                        self.append_status("📱 已扫码，等待确认...", replace_last=True)
                    elif status['status'] == 'expired':
                        self.append_status("⏰ 二维码已过期，请重新登录")
                        self.close_qr_window()
                        return False
                    else:
                        self.append_status(f"❌ 登录出错: {status['message']}")
                        self.close_qr_window()
                        return False
                    
                    attempt += 1
                    await asyncio.sleep(3)
                
                self.append_status("⏰ 登录超时，请重新登录")
                self.close_qr_window()
                return False
        except Exception as e:
            self.append_status(f"❌ 扫码登录异常: {str(e)}")
            self.close_qr_window()
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
            self.append_status(f"❌ 获取用户信息失败: {str(e)}")
            return {}
    
    def show_qr_code(self, image: Image.Image):
        """在新窗口中显示二维码"""
        self.close_qr_window()
        
        # 创建现代化的二维码窗口
        self.qr_window = ctk.CTkToplevel(self.root)
        self.qr_window.title("🔑 扫码登录")
        self.qr_window.geometry("400x500")
        self.qr_window.resizable(False, False)
        
        # 设置窗口属性
        self.qr_window.lift()
        self.qr_window.focus_force()
        self.qr_window.wm_attributes("-alpha", 0.98)
        
        # 主容器
        main_container = ctk.CTkFrame(self.qr_window, corner_radius=20)
        main_container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # 标题区域
        title_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        title_frame.pack(fill="x", padx=20, pady=(20, 10))
        
        title_label = ctk.CTkLabel(
            title_frame,
            text="🔑 扫码登录",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack()
        
        subtitle_label = ctk.CTkLabel(
            title_frame,
            text="请使用Bilibili手机客户端扫描下方二维码",
            font=ctk.CTkFont(size=14),
            text_color=("gray60", "gray40")
        )
        subtitle_label.pack(pady=(5, 0))
        
        # 二维码容器
        qr_container = ctk.CTkFrame(main_container, corner_radius=15)
        qr_container.pack(padx=20, pady=20)
        
        # 调整图像大小并添加边框
        image = image.resize((280, 280), Image.LANCZOS)
        self.qr_image = ImageTk.PhotoImage(image)
        
        self.qr_label = ctk.CTkLabel(
            qr_container, 
            image=self.qr_image, 
            text="",
            corner_radius=10
        )
        self.qr_label.pack(padx=15, pady=15)
        
        # 说明文字
        info_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        info_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        steps = [
            "1️⃣ 打开Bilibili手机客户端",
            "2️⃣ 点击右下角「我的」",
            "3️⃣ 点击右上角扫码图标",
            "4️⃣ 扫描上方二维码并确认登录"
        ]
        
        for step in steps:
            step_label = ctk.CTkLabel(
                info_frame,
                text=step,
                font=ctk.CTkFont(size=12),
                anchor="w"
            )
            step_label.pack(fill="x", pady=2)
        
        # 按钮区域
        button_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        button_frame.pack(fill="x", padx=20, pady=(10, 20))
        
        close_button = ctk.CTkButton(
            button_frame,
            text="❌ 关闭",
            command=self.close_qr_window,
            height=35,
            corner_radius=17,
            font=ctk.CTkFont(size=14)
        )
        close_button.pack()
        
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
    
    def update_login_status(self, status, is_logged_in=False):
        """更新登录状态显示"""
        if self.login_status_label and self.login_status_label.winfo_exists():
            self.login_status_label.configure(text=status)
            
        # 更新状态指示器颜色
        if self.login_status_indicator and self.login_status_indicator.winfo_exists():
            if is_logged_in:
                self.login_status_indicator.configure(fg_color="#22c55e")  # 绿色
                self.login_button.configure(text="✅ 已登录")
            else:
                self.login_status_indicator.configure(fg_color="#ef4444")  # 红色
                self.login_button.configure(text="🔑 扫码登录")
        
    def append_status(self, text, replace_last=False):
        """向状态文本框添加文本"""
        if replace_last:
            self.status_textbox.delete("end-1c linestart", "end-1c")
        
        # 添加时间戳
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        formatted_text = f"[{timestamp}] {text}\n"
        
        self.status_textbox.insert("end", formatted_text)
        self.status_textbox.see("end")
        self.root.update()
        
    def start_download(self):
        """开始下载视频"""
        if not self.video_list:
            self.append_status("❌ 请先添加视频到下载列表!")
            return
            
        # 解析选中的质量
        quality_text = self.quality_var.get()
        quality = int(quality_text.split(":")[0])
        
        output_dir = self.output_entry.get().strip()
        if not output_dir:
            output_dir = "./downloads"
            
        # 更新下载按钮状态
        self.download_button.configure(state="disabled", text="⏳ 下载中...")
        
        # 重置总体进度
        self.overall_progress_bar.set(0)
        self.overall_progress_label.configure(text=f"总体进度: 0/{len(self.video_list)}")
        
        # 在后台线程中执行下载
        self.download_thread = threading.Thread(
            target=self.download_videos, 
            args=(quality, output_dir)
        )
        self.download_thread.daemon = True
        self.download_thread.start()
        
    def download_videos(self, quality, output_dir):
        """在后台线程中下载所有视频"""
        try:
            total_videos = len(self.video_list)
            self.append_status(f"🚀 开始下载 {total_videos} 个视频...")
            
            import concurrent.futures
            max_workers = min(3, total_videos)
            
            def download_single_video(video_item):
                """下载单个视频"""
                self.root.after(0, lambda: self.update_video_status(video_item, "准备下载...", 0))
                
                async def download_task():
                    init_result = await self.downloader.init_client()
                    if not init_result:
                        self.root.after(0, lambda: self.update_video_status(video_item, "初始化失败", 0))
                        return False
                    
                    def progress_callback(status, progress):
                        self.root.after(0, lambda: self.update_video_status(video_item, status, progress))
                    
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
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_video = {
                    executor.submit(download_single_video, video): video 
                    for video in self.video_list
                }
                
                success_count = 0
                completed_count = 0
                
                for future in concurrent.futures.as_completed(future_to_video):
                    video_item, success = future.result()
                    completed_count += 1
                    
                    if success:
                        success_count += 1
                        self.root.after(0, lambda v=video_item: self.update_video_status(v, "✅ 下载完成", 1.0))
                    else:
                        self.root.after(0, lambda v=video_item: self.update_video_status(v, "❌ 下载失败", 0))
                    
                    # 更新总体进度
                    overall_progress = completed_count / total_videos
                    self.root.after(0, lambda p=overall_progress, c=completed_count, t=total_videos: (
                        self.overall_progress_bar.set(p),
                        self.overall_progress_label.configure(text=f"总体进度: {c}/{t}")
                    ))
                
                # 显示最终结果
                if success_count == total_videos:
                    self.root.after(0, lambda: self.append_status(f"🎉 全部下载完成! {success_count}/{total_videos} 个视频下载成功"))
                else:
                    self.root.after(0, lambda: self.append_status(f"📊 下载完成: {success_count}/{total_videos} 个视频下载成功"))
                
        except Exception as e:
            self.append_status(f"❌ 下载过程中出现错误: {str(e)}")
        finally:
            # 重新启用下载按钮
            def reset_button():
                if self.download_button.winfo_exists():
                    self.download_button.configure(state="normal", text="🚀 开始下载")
            
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