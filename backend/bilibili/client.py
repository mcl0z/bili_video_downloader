import httpx
import hashlib
import time
import urllib.parse
from typing import Optional, Dict, Any, List
import json
import re


class BilibiliClient:
    """Bilibili API 客户端"""
    
    def __init__(self):
        self.session = httpx.AsyncClient(
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': 'https://www.bilibili.com/'
            },
            timeout=30.0
        )
        self.cookies = {}
        self.wbi_keys = {}
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.aclose()
    
    def set_cookies(self, cookies: Dict[str, str]):
        """设置cookies"""
        self.cookies.update(cookies)
        for key, value in cookies.items():
            self.session.cookies.set(key, value)
    
    async def get_wbi_keys(self) -> Dict[str, str]:
        """获取WBI签名密钥"""
        try:
            response = await self.session.get('https://api.bilibili.com/x/web-interface/nav')
            data = response.json()
            
            if data['code'] == 0 and 'wbi_img' in data['data']:
                img_url = data['data']['wbi_img']['img_url']
                sub_url = data['data']['wbi_img']['sub_url']
                
                img_key = img_url.split('/')[-1].split('.')[0]
                sub_key = sub_url.split('/')[-1].split('.')[0]
                
                self.wbi_keys = {'img_key': img_key, 'sub_key': sub_key}
                return self.wbi_keys
        except Exception as e:
            print(f"获取WBI密钥失败: {e}")
        
        return {}
    
    def generate_wbi_signature(self, params: Dict[str, Any]) -> str:
        """生成WBI签名"""
        if not self.wbi_keys:
            return ""
        
        # 混合密钥
        mixin_key_enc_tab = [
            46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
            33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
            61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
            36, 20, 34, 44, 52
        ]
        
        img_key = self.wbi_keys.get('img_key', '')
        sub_key = self.wbi_keys.get('sub_key', '')
        raw_wbi_key = img_key + sub_key
        
        wbi_key = ''.join([raw_wbi_key[i] for i in mixin_key_enc_tab])[:32]
        
        # 添加时间戳
        params['wts'] = int(time.time())

        # 过滤特殊字符并排序参数
        filtered_params = {}
        for k, v in params.items():
            # 过滤 value 中的 "!'()*" 字符
            str_v = str(v)
            filtered_v = ''.join(filter(lambda chr: chr not in "!'()*", str_v))
            filtered_params[k] = filtered_v

        sorted_params = sorted(filtered_params.items())
        query_string = urllib.parse.urlencode(sorted_params)

        # 生成签名
        sign_string = query_string + wbi_key
        sign = hashlib.md5(sign_string.encode()).hexdigest()

        print(f"WBI签名调试:")
        print(f"  原始参数: {params}")
        print(f"  过滤后参数: {filtered_params}")
        print(f"  查询字符串: {query_string}")
        print(f"  签名字符串长度: {len(sign_string)}")
        print(f"  w_rid: {sign}")

        return sign
    
    async def get_user_info(self) -> Dict[str, Any]:
        """获取用户信息"""
        try:
            response = await self.session.get('https://api.bilibili.com/x/web-interface/nav')
            return response.json()
        except Exception as e:
            return {'code': -1, 'message': str(e), 'data': {}}
    
    async def get_video_info(self, bvid: Optional[str] = None, aid: Optional[int] = None) -> Dict[str, Any]:
        """获取视频信息"""
        if not bvid and not aid:
            return {'code': -400, 'message': '缺少视频ID参数'}
        
        params = {}
        if bvid:
            params['bvid'] = bvid
        if aid:
            params['aid'] = aid
        
        try:
            response = await self.session.get(
                'https://api.bilibili.com/x/web-interface/view',
                params=params
            )
            return response.json()
        except Exception as e:
            return {'code': -1, 'message': str(e), 'data': {}}
    
    async def search_videos(self, keyword: str, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """搜索视频"""
        try:
            print(f"搜索关键词: {keyword}, 页码: {page}")

            # 确保有WBI密钥
            if not self.wbi_keys:
                await self.get_wbi_keys()

            # 使用WBI签名的分类搜索API
            params = {
                'search_type': 'video',
                'keyword': keyword,
                'page': page,
                'order': 'totalrank',
                'duration': 0,
                'tids': 0
            }

            # 生成WBI签名
            params_copy = params.copy()
            w_sign = self.generate_wbi_signature(params_copy)
            params['w_rid'] = w_sign
            params['wts'] = params_copy['wts']  # 添加时间戳

            # 设置必要的headers
            headers = {
                'Referer': 'https://search.bilibili.com/',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }

            # 先访问bilibili.com获取必要的cookies
            await self.session.get('https://www.bilibili.com')

            response = await self.session.get(
                'https://api.bilibili.com/x/web-interface/wbi/search/type',
                params=params,
                headers=headers
            )

            print(f"搜索API响应状态: {response.status_code}")

            # 检查响应内容
            response_text = response.text
            print(f"搜索API响应内容前100字符: {response_text[:100]}")

            if not response_text.strip():
                print("搜索API返回空响应")
                return {'code': -1, 'message': '搜索API返回空响应', 'data': {}}

            try:
                result = response.json()
                print(f"搜索API解析成功, code: {result.get('code')}")

                # 如果成功，打印结果数量
                if result.get('code') == 0 and result.get('data', {}).get('result'):
                    print(f"搜索到 {len(result['data']['result'])} 个结果")

                return result
            except Exception as json_error:
                print(f"JSON解析失败: {json_error}")
                print(f"响应内容: {response_text}")
                return {'code': -1, 'message': f'JSON解析失败: {json_error}', 'data': {}}

        except Exception as e:
            print(f"搜索视频异常: {e}")
            return {'code': -1, 'message': str(e), 'data': {}}
    
    async def get_popular_videos(self, pn: int = 1, ps: int = 20) -> Dict[str, Any]:
        """获取热门视频"""
        try:
            response = await self.session.get(
                'https://api.bilibili.com/x/web-interface/popular',
                params={'pn': pn, 'ps': ps}
            )
            return response.json()
        except Exception as e:
            return {'code': -1, 'message': str(e), 'data': {}}
    
    async def get_video_stream_url(self, bvid: str, cid: int, qn: int = 80) -> Dict[str, Any]:
        """获取视频流地址"""
        # 确保有WBI密钥
        if not self.wbi_keys:
            await self.get_wbi_keys()

        params = {
            'bvid': bvid,
            'cid': cid,
            'qn': qn,
            'fnval': 4048,  # 获取所有可用DASH格式视频流
            'fnver': 0,
            'fourk': 1,
            'platform': 'html5'
        }

        try:
            # 生成WBI签名
            w_sign = self.generate_wbi_signature(params.copy())
            params['w_rid'] = w_sign

            # 尝试使用WBI签名的新API
            response = await self.session.get(
                'https://api.bilibili.com/x/player/wbi/playurl',
                params=params
            )
            result = response.json()

            # 如果新API失败，尝试旧API
            if result.get('code') != 0:
                print(f"WBI API失败: {result.get('message')}, 尝试旧API")
                # 移除WBI签名参数
                old_params = {
                    'bvid': bvid,
                    'cid': cid,
                    'qn': qn,
                    'fnval': 16,  # 基础DASH格式
                    'fnver': 0,
                    'fourk': 1
                }

                response = await self.session.get(
                    'https://api.bilibili.com/x/player/playurl',
                    params=old_params
                )
                result = response.json()

            return result
        except Exception as e:
            print(f"获取视频流异常: {e}")
            return {'code': -1, 'message': str(e), 'data': {}}

    async def get_comments(self, type: int = 1, oid: int = 0, pn: int = 1, ps: int = 20, sort: int = 0) -> Dict[str, Any]:
        """获取评论列表"""
        params = {
            'type': type,
            'oid': oid,
            'pn': pn,
            'ps': ps,
            'sort': sort
        }

        try:
            response = await self.session.get(
                'https://api.bilibili.com/x/v2/reply',
                params=params
            )
            return response.json()
        except Exception as e:
            return {'code': -1, 'message': str(e), 'data': {}}

    async def add_comment(self, type: int = 1, oid: int = 0, message: str = "",
                         root: int = 0, parent: int = 0, plat: int = 1) -> Dict[str, Any]:
        """发表评论"""
        # 获取CSRF token
        csrf_token = self.cookies.get('bili_jct', '')

        data = {
            'type': type,
            'oid': oid,
            'message': message,
            'root': root,
            'parent': parent,
            'plat': plat,
            'csrf': csrf_token
        }

        try:
            response = await self.session.post(
                'https://api.bilibili.com/x/v2/reply/add',
                data=data
            )
            return response.json()
        except Exception as e:
            return {'code': -1, 'message': str(e), 'data': {}}

    async def like_comment(self, type: int = 1, oid: int = 0, rpid: int = 0, action: int = 1) -> Dict[str, Any]:
        """点赞评论"""
        csrf_token = self.cookies.get('bili_jct', '')

        data = {
            'type': type,
            'oid': oid,
            'rpid': rpid,
            'action': action,
            'csrf': csrf_token
        }

        try:
            response = await self.session.post(
                'https://api.bilibili.com/x/v2/reply/action',
                data=data
            )
            return response.json()
        except Exception as e:
            return {'code': -1, 'message': str(e), 'data': {}}

    async def like_video(self, bvid: str, like: int) -> Dict[str, Any]:
        """点赞视频"""
        csrf_token = self.cookies.get('bili_jct', '')

        data = {
            'bvid': bvid,
            'like': like,
            'csrf': csrf_token
        }

        try:
            response = await self.session.post(
                'https://api.bilibili.com/x/web-interface/archive/like',
                data=data
            )
            return response.json()
        except Exception as e:
            return {'code': -1, 'message': str(e), 'data': {}}

    async def coin_video(self, bvid: str, multiply: int, select_like: str = "0") -> Dict[str, Any]:
        """投币"""
        csrf_token = self.cookies.get('bili_jct', '')

        data = {
            'bvid': bvid,
            'multiply': multiply,
            'select_like': select_like,
            'csrf': csrf_token
        }

        try:
            response = await self.session.post(
                'https://api.bilibili.com/x/web-interface/coin/add',
                data=data
            )
            return response.json()
        except Exception as e:
            return {'code': -1, 'message': str(e), 'data': {}}

    async def favorite_video(self, rid: int, type: int = 2, add_media_ids: str = "", del_media_ids: str = "") -> Dict[str, Any]:
        """收藏视频"""
        csrf_token = self.cookies.get('bili_jct', '')

        data = {
            'rid': rid,
            'type': type,
            'add_media_ids': add_media_ids,
            'del_media_ids': del_media_ids,
            'csrf': csrf_token
        }

        try:
            response = await self.session.post(
                'https://api.bilibili.com/x/v3/fav/resource/deal',
                data=data
            )
            return response.json()
        except Exception as e:
            return {'code': -1, 'message': str(e), 'data': {}}

    async def get_user_info_by_mid(self, mid: int) -> Dict[str, Any]:
        """根据mid获取用户信息"""
        try:
            response = await self.session.get(
                'https://api.bilibili.com/x/space/acc/info',
                params={'mid': mid}
            )
            return response.json()
        except Exception as e:
            return {'code': -1, 'message': str(e), 'data': {}}

    async def get_user_stat(self, mid: int) -> Dict[str, Any]:
        """获取用户统计信息（粉丝数等）"""
        try:
            response = await self.session.get(
                'https://api.bilibili.com/x/relation/stat',
                params={'vmid': mid}
            )
            return response.json()
        except Exception as e:
            return {'code': -1, 'message': str(e), 'data': {}}

    async def get_user_videos(self, mid: int, pn: int = 1, ps: int = 10) -> Dict[str, Any]:
        """获取用户投稿视频"""
        try:
            response = await self.session.get(
                'https://api.bilibili.com/x/space/arc/search',
                params={
                    'mid': mid,
                    'pn': pn,
                    'ps': ps,
                    'order': 'pubdate'
                }
            )
            return response.json()
        except Exception as e:
            return {'code': -1, 'message': str(e), 'data': {}}

    async def get_videos_by_tid(self, tid: int, pn: int = 1, ps: int = 20) -> Dict[str, Any]:
        """根据分区ID获取视频"""
        try:
            response = await self.session.get(
                'https://api.bilibili.com/x/web-interface/newlist',
                params={
                    'rid': tid,
                    'pn': pn,
                    'ps': ps
                }
            )
            return response.json()
        except Exception as e:
            return {'code': -1, 'message': str(e), 'data': {}}

    async def get_recommend_videos(self, fresh_type: int = 3) -> Dict[str, Any]:
        """获取推荐视频"""
        try:
            response = await self.session.get(
                'https://api.bilibili.com/x/web-interface/index/top/rcmd',
                params={
                    'fresh_type': fresh_type,  # 3表示获取推荐视频
                    'version': 1,
                    'ps': 20
                }
            )
            return response.json()
        except Exception as e:
            return {'code': -1, 'message': str(e), 'data': {}}

    async def get_feed_videos(self) -> Dict[str, Any]:
        """获取首页推荐feed流"""
        try:
            response = await self.session.get(
                'https://api.bilibili.com/x/web-interface/wbi/index/top/feed/rcmd',
                params={
                    'y_num': 5,
                    'fresh_type': 3,
                    'feed_version': 'V8',
                    'fresh_idx_1h': 1,
                    'fetch_row': 1,
                    'fresh_idx': 1,
                    'brush': 0,
                    'homepage_ver': 1,
                    'ps': 12
                }
            )
            return response.json()
        except Exception as e:
            return {'code': -1, 'message': str(e), 'data': {}}
