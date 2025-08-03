import qrcode
import io
import base64
import time
import httpx
from typing import Dict, Any, Optional, Tuple


class BilibiliAuth:
    """Bilibili 登录认证"""
    
    def __init__(self):
        self.session = httpx.AsyncClient(
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': 'https://passport.bilibili.com/login'
            },
            timeout=30.0
        )
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.aclose()
    
    async def get_qr_code(self) -> Tuple[Optional[str], Optional[str]]:
        """获取登录二维码"""
        try:
            # 获取二维码登录URL
            response = await self.session.get('https://passport.bilibili.com/x/passport-login/web/qrcode/generate')
            data = response.json()
            
            if data['code'] != 0:
                return None, None
            
            qr_url = data['data']['url']
            qrcode_key = data['data']['qrcode_key']
            
            # 生成二维码图片
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_url)
            qr.make(fit=True)
            
            # 转换为base64图片
            img = qr.make_image(fill_color="black", back_color="white")
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='PNG')
            img_str = base64.b64encode(img_buffer.getvalue()).decode()
            
            return f"data:image/png;base64,{img_str}", qrcode_key
            
        except Exception as e:
            print(f"获取二维码失败: {e}")
            return None, None
    
    async def check_qr_status(self, qrcode_key: str) -> Dict[str, Any]:
        """检查二维码扫描状态"""
        try:
            response = await self.session.get(
                'https://passport.bilibili.com/x/passport-login/web/qrcode/poll',
                params={'qrcode_key': qrcode_key}
            )
            data = response.json()
            
            if data['code'] != 0:
                return {'status': 'error', 'message': data.get('message', '未知错误')}
            
            code = data['data']['code']
            
            if code == 86101:
                return {'status': 'waiting', 'message': '未扫码'}
            elif code == 86090:
                return {'status': 'scanned', 'message': '已扫码，等待确认'}
            elif code == 0:
                # 登录成功，提取cookies
                cookies = {}
                try:
                    # 尝试不同的方式提取cookies
                    if hasattr(response.cookies, 'items'):
                        # httpx.Cookies对象
                        for name, value in response.cookies.items():
                            cookies[name] = value
                    else:
                        # 其他格式
                        cookies = dict(response.cookies)
                except Exception as e:
                    print(f"提取cookies失败: {e}")
                    # 从Set-Cookie头部提取
                    set_cookie_headers = response.headers.get_list('set-cookie')
                    for header in set_cookie_headers:
                        if '=' in header:
                            name, value = header.split('=', 1)
                            value = value.split(';')[0]  # 移除其他属性
                            cookies[name.strip()] = value.strip()
                
                return {
                    'status': 'success',
                    'message': '登录成功',
                    'cookies': cookies,
                    'url': data['data'].get('url', '')
                }
            elif code == 86038:
                return {'status': 'expired', 'message': '二维码已过期'}
            else:
                return {'status': 'error', 'message': f'未知状态码: {code}'}
                
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    async def login_with_qr(self) -> Dict[str, Any]:
        """二维码登录流程"""
        # 获取二维码
        qr_image, qrcode_key = await self.get_qr_code()
        
        if not qr_image or not qrcode_key:
            return {'status': 'error', 'message': '获取二维码失败'}
        
        return {
            'status': 'qr_ready',
            'qr_image': qr_image,
            'qrcode_key': qrcode_key,
            'message': '请使用Bilibili APP扫描二维码'
        }
    
    async def validate_cookies(self, cookies: Dict[str, str]) -> bool:
        """验证cookies是否有效"""
        try:
            # 设置cookies
            for key, value in cookies.items():
                self.session.cookies.set(key, value)
            
            # 检查登录状态
            response = await self.session.get('https://api.bilibili.com/x/web-interface/nav')
            data = response.json()
            
            return data['code'] == 0 and data['data'].get('isLogin', False)
            
        except Exception:
            return False
