#!/usr/bin/env python3

import asyncio
import sys
import os
import re
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn
from rich.prompt import Prompt, Confirm
from rich.layout import Layout
from rich.live import Live
from rich.text import Text
from rich import box
from rich.align import Align
from rich.columns import Columns
from rich.rule import Rule

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from video_downloader import VideoDownloader


class TUIDownloader:
    
    def __init__(self):
        self.console = Console()
        self.downloader = VideoDownloader()
        self.download_queue: List[Dict] = []
        self.max_concurrent = 3
        self.quality_map = {
            "1": (112, "1080p+"),
            "2": (80, "1080p"),
            "3": (64, "720p"),
            "4": (32, "480p"),
            "5": (16, "360p")
        }
        
    def show_banner(self):
        self.console.print("\n[bold yellow]Bilibili 视频批量下载工具 (TUI版)[/bold yellow]")
        self.console.print("[dim]使用 Rich 库构建的终端用户界面[/dim]")
        self.console.print("[cyan]支持批量下载 | 自动提取BV号 | 实时进度显示[/cyan]\n")
    
    def extract_bvid_from_url(self, text: str) -> List[str]:
        """从文本中提取BV号"""
        bvids = []
        
        # 匹配BV号的正则表达式
        bvid_pattern = r'BV[a-zA-Z0-9]+'
        
        # 匹配完整URL的正则表达式
        url_pattern = r'https?://(?:www\.)?bilibili\.com/video/([a-zA-Z0-9]+)'
        
        # 提取BV号
        bvid_matches = re.findall(bvid_pattern, text, re.IGNORECASE)
        bvids.extend(bvid_matches)
        
        # 从URL中提取
        url_matches = re.findall(url_pattern, text)
        for match in url_matches:
            if match.startswith('BV'):
                bvids.append(match)
        
        # 去重并返回
        return list(set(bvids))
    
    def show_main_menu(self) -> str:
        self.console.print("\n[bold yellow]主菜单[/bold yellow]")
        self.console.print("[white]请选择要执行的操作:[/white]\n")
        
        menu_items = [
            ("1", "添加下载任务", "支持URL粘贴和BV号输入"),
            ("2", "查看下载队列", "显示所有下载任务状态"),
            ("3", "开始批量下载", "执行队列中的所有任务"),
            ("4", "清空下载队列", "删除所有待下载任务"),
            ("5", "登录/重新登录", "扫码登录B站账号"),
            ("6", "设置并发数量", "调整同时下载的任务数"),
            ("0", "退出程序", "关闭下载工具")
        ]
        
        for option, function, description in menu_items:
            self.console.print(
                f"[cyan]{option}.[/cyan] [bold white]{function}[/bold white] "
                f"[dim]- {description}[/dim]"
            )
        
        # 显示当前队列状态
        if self.download_queue:
            self.console.print(f"\n[dim]当前队列: {len(self.download_queue)} 个任务[/dim]")
        
        self.console.print(f"[dim]当前并发数: {self.max_concurrent}[/dim]")
        
        choice = Prompt.ask(
            "\n[bold cyan]请选择操作[/bold cyan]",
            choices=["0", "1", "2", "3", "4", "5", "6"],
            default="1"
        )
        return choice
    
    def add_download_task(self):
        self.console.print("\n[bold green]添加下载任务[/bold green]")
        self.console.print("[white]支持以下输入方式:[/white]")
        self.console.print("• 直接粘贴B站视频URL（自动提取BV号）")
        self.console.print("• 直接输入BV号（如: BV1234567890）")
        self.console.print("• 混合输入多个URL和BV号")
        self.console.print("• 多个项目用空格或换行分隔\n")
        
        bvids = []
        while True:
            bvid_input = Prompt.ask(
                "[bold cyan]请输入URL或BV号[/bold cyan] (直接回车结束)",
                default="",
                show_default=False
            )
            if not bvid_input:
                break
            
            # 提取BV号
            extracted_bvids = self.extract_bvid_from_url(bvid_input)
            
            # 如果没有提取到BV号，可能是直接输入的BV号
            if not extracted_bvids:
                # 检查是否是BV号
                if re.match(r'^BV[a-zA-Z0-9]+$', bvid_input.strip(), re.IGNORECASE):
                    extracted_bvids = [bvid_input.strip()]
            
            # 添加到列表（去重）
            for bvid in extracted_bvids:
                if bvid and bvid not in bvids:
                    bvids.append(bvid)
                    self.console.print(f"  [green]✓[/green] 已添加: [yellow]{bvid}[/yellow]")
        
        if not bvids:
            self.console.print("\n[yellow]⚠ 未添加任何视频[/yellow]")
            return
        
        # 显示质量选择
        self.console.print("\n[bold blue]请选择视频质量:[/bold blue]")
        
        quality_info = {
            "1": (112, "1080p+", "高清画质"),
            "2": (80, "1080p", "全高清"),
            "3": (64, "720p", "高清"),
            "4": (32, "480p", "标清"),
            "5": (16, "360p", "流畅")
        }
        
        for key, (code, desc, note) in quality_info.items():
            self.console.print(f"  {key}. {desc} ({note})")
        
        quality_choice = Prompt.ask(
            "\n[bold cyan]请选择质量[/bold cyan]",
            choices=list(self.quality_map.keys()),
            default="4"
        )
        quality_code, quality_desc = self.quality_map[quality_choice]
        
        # 输出目录选择
        output_dir = Prompt.ask(
            "\n[bold cyan]输出目录[/bold cyan]",
            default="./downloads"
        )
        
        # 添加任务到队列
        for bvid in bvids:
            task = {
                "bvid": bvid,
                "quality": quality_code,
                "quality_desc": quality_desc,
                "output_dir": output_dir,
                "status": "待下载",
                "added_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            self.download_queue.append(task)
        
        # 显示成功消息
        self.console.print(f"\n[bold green]✓ 成功添加 {len(bvids)} 个下载任务[/bold green]")
        self.console.print(f"[dim]质量: {quality_desc} | 输出目录: {output_dir}[/dim]\n")
    
    def show_download_queue(self):
        if not self.download_queue:
            self.console.print("\n[bold yellow]⚠ 下载队列为空[/bold yellow]")
            self.console.print("[dim]请先添加下载任务[/dim]\n")
            return
        
        # 统计任务状态
        status_count = {"待下载": 0, "下载中": 0, "已完成": 0, "失败": 0}
        for task in self.download_queue:
            status_count[task["status"]] = status_count.get(task["status"], 0) + 1
        
        # 显示统计信息
        self.console.print(f"\n[bold blue]下载队列统计[/bold blue]")
        self.console.print(
            f"[cyan]总任务: {len(self.download_queue)}[/cyan] | "
            f"[white]待下载: {status_count['待下载']}[/white] | "
            f"[yellow]下载中: {status_count['下载中']}[/yellow] | "
            f"[green]已完成: {status_count['已完成']}[/green] | "
            f"[red]失败: {status_count['失败']}[/red]\n"
        )
        
        # 显示任务列表
        self.console.print("[bold green]下载任务列表[/bold green]")
        
        for idx, task in enumerate(self.download_queue, 1):
            status_style = {
                "已完成": "green",
                "下载中": "yellow", 
                "失败": "red",
                "待下载": "white"
            }.get(task["status"], "white")
            
            # 状态图标
            status_icon = {
                "已完成": "✓",
                "下载中": "⟳",
                "失败": "✗", 
                "待下载": "⏸"
            }.get(task["status"], "?")
            
            self.console.print(
                f"[cyan]{idx}.[/cyan] [yellow]{task['bvid']}[/yellow] "
                f"[green]{task['quality_desc']}[/green] "
                f"[blue]{task['output_dir']}[/blue] "
                f"[{status_style}]{status_icon} {task['status']}[/{status_style}] "
                f"[dim]{task['added_time']}[/dim]"
            )
        
        self.console.print()
    
    def clear_queue(self):
        if not self.download_queue:
            self.console.print("\n[yellow]下载队列已经为空[/yellow]")
            return
        
        if Confirm.ask(f"\n确定要清空 {len(self.download_queue)} 个下载任务吗?"):
            self.download_queue.clear()
            self.console.print("[green]✓[/green] 下载队列已清空")
        else:
            self.console.print("[dim]操作已取消[/dim]")
    
    def set_concurrent_limit(self):
        self.console.print(f"\n[bold green]设置并发下载数量[/bold green]")
        self.console.print(f"[white]当前并发数: [cyan]{self.max_concurrent}[/cyan][/white]")
        self.console.print("[dim]建议范围: 1-10 (过高可能导致限流)[/dim]\n")
        
        concurrent = Prompt.ask(
            "[bold cyan]请输入并发数量[/bold cyan]",
            default=str(self.max_concurrent)
        )
        
        try:
            concurrent_num = int(concurrent)
            if 1 <= concurrent_num <= 10:
                self.max_concurrent = concurrent_num
                self.console.print(f"[green]✓[/green] 并发数量已设置为: {self.max_concurrent}")
            else:
                self.console.print("[red]✗[/red] 并发数量必须在 1-10 之间")
        except ValueError:
            self.console.print("[red]✗[/red] 请输入有效的数字")
    
    async def login(self):
        self.console.print("\n[bold green]登录 Bilibili[/bold green]\n")
        
        has_cookies = self.downloader.load_cookies()
        
        if has_cookies:
            if Confirm.ask("检测到已保存的登录信息，是否重新登录?", default=False):
                success = await self.downloader._qr_login_async()
                if success:
                    self.console.print("[green]✓[/green] 登录成功!")
                else:
                    self.console.print("[red]✗[/red] 登录失败")
            else:
                self.console.print("[green]✓[/green] 使用已保存的登录信息")
        else:
            self.console.print("[yellow]未找到登录信息，需要扫码登录[/yellow]\n")
            success = await self.downloader._qr_login_async()
            if success:
                self.console.print("[green]✓[/green] 登录成功!")
            else:
                self.console.print("[red]✗[/red] 登录失败")
    
    async def start_batch_download(self):
        if not self.download_queue:
            self.console.print("\n[yellow]下载队列为空，请先添加下载任务[/yellow]")
            return
        
        if not await self.downloader.init_client():
            self.console.print("[red]✗[/red] 初始化下载器失败，请先登录")
            return
        
        self.console.print(f"\n[bold green]开始批量下载 ({len(self.download_queue)} 个任务)[/bold green]")
        self.console.print(f"[cyan]并发数: {self.max_concurrent}[/cyan]\n")
        
        success_count = 0
        fail_count = 0
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=self.console
        ) as progress:
            
            overall_task = progress.add_task(
                "[cyan]总体进度", 
                total=len(self.download_queue)
            )
            
            task_progress_map = {}
            
            async def download_single_task(task_info, idx):
                nonlocal success_count, fail_count
                
                async with semaphore:
                    task_info["status"] = "下载中"
                    
                    download_task = progress.add_task(
                        f"[yellow]({idx}/{len(self.download_queue)}) {task_info['bvid']}", 
                        total=100
                    )
                    task_progress_map[task_info['bvid']] = download_task
                    
                    def update_progress(status: str, percent: float):
                        progress.update(download_task, completed=int(percent * 100))
                    
                    try:
                        success = await self.downloader.download_video(
                            task_info["bvid"],
                            task_info["quality"],
                            task_info["output_dir"],
                            progress_callback=update_progress
                        )
                        
                        if success:
                            task_info["status"] = "已完成"
                            success_count += 1
                            progress.update(download_task, completed=100)
                        else:
                            task_info["status"] = "失败"
                            fail_count += 1
                            
                    except Exception as e:
                        task_info["status"] = "失败"
                        fail_count += 1
                        self.console.print(f"[red]下载 {task_info['bvid']} 时出错: {e}[/red]")
                    
                    progress.update(overall_task, advance=1)
            
            tasks = [
                download_single_task(task, idx) 
                for idx, task in enumerate(self.download_queue, 1)
            ]
            
            await asyncio.gather(*tasks)
        
        self.console.print(f"\n[bold]下载完成![/bold]")
        self.console.print(f"[green]成功: {success_count}[/green] | [red]失败: {fail_count}[/red]")
    
    async def run(self):
        self.show_banner()
        
        if not self.downloader.load_cookies():
            self.console.print("\n[yellow]未检测到登录信息，请先登录[/yellow]")
            await self.login()
        else:
            self.console.print("\n[green]✓[/green] 已加载登录信息")
        
        while True:
            try:
                choice = self.show_main_menu()
                
                if choice == "0":
                    if Confirm.ask("\n确定要退出吗?", default=False):
                        self.console.print("\n[cyan]感谢使用，再见！[/cyan]")
                        break
                
                elif choice == "1":
                    self.add_download_task()
                
                elif choice == "2":
                    self.show_download_queue()
                
                elif choice == "3":
                    await self.start_batch_download()
                
                elif choice == "4":
                    self.clear_queue()
                
                elif choice == "5":
                    await self.login()
                
                elif choice == "6":
                    self.set_concurrent_limit()
                
            except KeyboardInterrupt:
                if Confirm.ask("\n\n检测到中断，确定要退出吗?", default=False):
                    self.console.print("\n[cyan]感谢使用，再见！[/cyan]")
                    break
            except Exception as e:
                self.console.print(f"\n[red]发生错误: {e}[/red]")
                import traceback
                traceback.print_exc()


async def main():
    tui = TUIDownloader()
    await tui.run()


if __name__ == "__main__":
    asyncio.run(main())
