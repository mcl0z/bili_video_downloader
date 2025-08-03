"""
Cookie管理器 - 用于持久化保存和加载用户cookies
"""

import json
import os
from pathlib import Path
from typing import Dict, Optional
import time


class CookieManager:
    """Cookie管理器"""
    
    def __init__(self, cookie_file: str = "user_cookies.json"):
        self.cookie_file = Path(cookie_file)
        self.cookies_data = {}
        self.load_cookies()
    
    def save_cookies(self, user_id: str, cookies: Dict[str, str], user_info: Optional[Dict] = None) -> bool:
        """保存用户cookies"""
        try:
            self.cookies_data[user_id] = {
                'cookies': cookies,
                'user_info': user_info or {},
                'saved_time': int(time.time()),
                'expires_time': int(time.time()) + (30 * 24 * 3600)  # 30天过期
            }
            
            with open(self.cookie_file, 'w', encoding='utf-8') as f:
                json.dump(self.cookies_data, f, ensure_ascii=False, indent=2)
            
            print(f"已保存用户 {user_id} 的cookies")
            return True
        except Exception as e:
            print(f"保存cookies失败: {e}")
            return False
    
    def load_cookies(self) -> bool:
        """加载所有cookies"""
        try:
            if self.cookie_file.exists():
                with open(self.cookie_file, 'r', encoding='utf-8') as f:
                    self.cookies_data = json.load(f)
                print(f"已加载 {len(self.cookies_data)} 个用户的cookies")
                return True
        except Exception as e:
            print(f"加载cookies失败: {e}")
        
        self.cookies_data = {}
        return False
    
    def get_cookies(self, user_id: str) -> Optional[Dict[str, str]]:
        """获取指定用户的cookies"""
        if user_id not in self.cookies_data:
            return None
        
        user_data = self.cookies_data[user_id]
        
        # 检查是否过期
        if int(time.time()) > user_data.get('expires_time', 0):
            print(f"用户 {user_id} 的cookies已过期")
            self.remove_cookies(user_id)
            return None
        
        return user_data.get('cookies')
    
    def get_user_info(self, user_id: str) -> Optional[Dict]:
        """获取用户信息"""
        if user_id not in self.cookies_data:
            return None
        
        return self.cookies_data[user_id].get('user_info')
    
    def remove_cookies(self, user_id: str) -> bool:
        """删除指定用户的cookies"""
        try:
            if user_id in self.cookies_data:
                del self.cookies_data[user_id]
                with open(self.cookie_file, 'w', encoding='utf-8') as f:
                    json.dump(self.cookies_data, f, ensure_ascii=False, indent=2)
                print(f"已删除用户 {user_id} 的cookies")
                return True
        except Exception as e:
            print(f"删除cookies失败: {e}")
        
        return False
    
    def get_all_users(self) -> Dict[str, Dict]:
        """获取所有用户信息"""
        result = {}
        current_time = int(time.time())
        
        for user_id, data in self.cookies_data.items():
            if current_time <= data.get('expires_time', 0):
                result[user_id] = {
                    'user_info': data.get('user_info', {}),
                    'saved_time': data.get('saved_time', 0),
                    'expires_time': data.get('expires_time', 0)
                }
        
        return result
    
    def cleanup_expired(self) -> int:
        """清理过期的cookies"""
        current_time = int(time.time())
        expired_users = []
        
        for user_id, data in self.cookies_data.items():
            if current_time > data.get('expires_time', 0):
                expired_users.append(user_id)
        
        for user_id in expired_users:
            self.remove_cookies(user_id)
        
        return len(expired_users)


# 全局cookie管理器实例
cookie_manager = CookieManager()
