from fastapi import APIRouter, HTTPException, Query, Form
from fastapi.responses import Response
from typing import Dict, Any, Optional
import httpx
import base64
from urllib.parse import quote, unquote
from ..bilibili.client import BilibiliClient
from .auth import get_client

router = APIRouter(prefix="/video", tags=["视频"])


@router.get("/info")
async def get_video_info(
    bvid: Optional[str] = Query(None, description="视频BVID"),
    aid: Optional[int] = Query(None, description="视频AID")
) -> Dict[str, Any]:
    """获取视频信息"""
    if not bvid and not aid:
        raise HTTPException(status_code=400, detail="请提供BVID或AID")
    
    try:
        # 创建临时客户端实例（无需登录）
        async with BilibiliClient() as client:
            result = await client.get_video_info(bvid=bvid, aid=aid)
            return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/popular")
async def get_popular_videos(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=50, description="每页数量")
) -> Dict[str, Any]:
    """获取热门视频"""
    try:
        async with BilibiliClient() as client:
            result = await client.get_popular_videos(pn=page, ps=page_size)
            return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/random")
async def get_random_videos(
    count: int = Query(20, ge=1, le=50, description="视频数量")
) -> Dict[str, Any]:
    """获取随机视频"""
    try:
        async with BilibiliClient() as client:
            import random

            # 从多个热门页面随机获取视频
            all_videos = []

            # 从前5页热门视频中随机选择
            for page in range(1, 6):
                try:
                    result = await client.get_popular_videos(pn=page, ps=20)

                    if result.get('code') == 0 and result.get('data', {}).get('list'):
                        videos = result['data']['list']
                        all_videos.extend(videos)
                except Exception as e:
                    print(f"获取第{page}页热门视频失败: {e}")
                    continue

            # 如果没有获取到足够的视频，尝试获取更多
            if len(all_videos) < count:
                try:
                    # 尝试获取推荐视频
                    result = await client.get_popular_videos(pn=1, ps=50)
                    if result.get('code') == 0 and result.get('data', {}).get('list'):
                        all_videos.extend(result['data']['list'])
                except Exception as e:
                    print(f"获取推荐视频失败: {e}")

            # 随机打乱并选择指定数量
            if all_videos:
                random.shuffle(all_videos)
                final_videos = all_videos[:count]
            else:
                final_videos = []

            print(f"随机视频API: 获取到 {len(final_videos)} 个视频")

            return {
                'code': 0,
                'message': '0',
                'data': {
                    'list': final_videos,
                    'no_more': True  # 随机视频不支持分页
                }
            }
    except Exception as e:
        print(f"随机视频API错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_videos(
    keyword: str = Query(..., description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=50, description="每页数量")
) -> Dict[str, Any]:
    """搜索视频"""
    try:
        async with BilibiliClient() as client:
            result = await client.search_videos(keyword=keyword, page=page, page_size=page_size)
            return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stream-url")
async def get_video_stream_url(
    bvid: str = Query(..., description="视频BVID"),
    cid: int = Query(..., description="视频CID"),
    qn: int = Query(80, description="视频质量")
) -> Dict[str, Any]:
    """获取视频流地址"""
    try:
        # 优先使用已登录的客户端
        client = get_client()
        if client:
            result = await client.get_video_stream_url(bvid=bvid, cid=cid, qn=qn)
        else:
            # 如果未登录，使用临时客户端
            async with BilibiliClient() as temp_client:
                result = await temp_client.get_video_stream_url(bvid=bvid, cid=cid, qn=qn)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/image-proxy")
async def image_proxy(url: str = Query(..., description="图片URL")) -> Response:
    """图片代理服务，解决Bilibili图片的跨域和Referer问题"""
    try:
        # 解码URL
        image_url = unquote(url)
        print(f"代理图片请求: {image_url}")  # 调试日志

        # 验证URL是否来自Bilibili
        if not any(domain in image_url for domain in ['hdslb.com', 'bilibili.com']):
            print(f"非Bilibili图片URL: {image_url}")
            raise HTTPException(status_code=400, detail="只允许代理Bilibili图片")

        # 创建HTTP客户端，设置正确的headers
        async with httpx.AsyncClient(
            follow_redirects=True,  # 允许重定向
            verify=False  # 暂时禁用SSL验证以避免证书问题
        ) as client:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': 'https://www.bilibili.com/',
                'Accept': 'image/webp,image/apng,image/avif,image/svg+xml,image/*,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Sec-Fetch-Dest': 'image',
                'Sec-Fetch-Mode': 'no-cors',
                'Sec-Fetch-Site': 'cross-site'
            }

            print(f"发送请求到: {image_url}")
            response = await client.get(image_url, headers=headers, timeout=15.0)
            print(f"响应状态码: {response.status_code}")

            if response.status_code == 200:
                # 获取内容类型
                content_type = response.headers.get('content-type', 'image/jpeg')
                print(f"图片类型: {content_type}, 大小: {len(response.content)} bytes")

                # 返回图片内容
                return Response(
                    content=response.content,
                    media_type=content_type,
                    headers={
                        'Cache-Control': 'public, max-age=3600',  # 缓存1小时
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Methods': 'GET',
                        'Access-Control-Allow-Headers': '*',
                        'Cross-Origin-Resource-Policy': 'cross-origin'
                    }
                )
            else:
                print(f"获取图片失败: {response.status_code} - {response.text}")
                # 如果是403错误，尝试不同的User-Agent
                if response.status_code == 403:
                    headers['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                    retry_response = await client.get(image_url, headers=headers, timeout=15.0)
                    if retry_response.status_code == 200:
                        return Response(
                            content=retry_response.content,
                            media_type=retry_response.headers.get('content-type', 'image/jpeg'),
                            headers={
                                'Cache-Control': 'public, max-age=3600',
                                'Access-Control-Allow-Origin': '*',
                                'Access-Control-Allow-Methods': 'GET',
                                'Access-Control-Allow-Headers': '*',
                                'Cross-Origin-Resource-Policy': 'cross-origin'
                            }
                        )

                raise HTTPException(status_code=response.status_code, detail=f"获取图片失败: {response.status_code}")

    except httpx.TimeoutException:
        print("图片请求超时")
        raise HTTPException(status_code=408, detail="请求超时")
    except Exception as e:
        print(f"代理图片异常: {str(e)}")
        raise HTTPException(status_code=500, detail=f"代理图片失败: {str(e)}")


@router.post("/like")
async def like_video(
    bvid: str = Form(...),
    like: int = Form(...)
) -> Dict[str, Any]:
    """点赞视频"""
    client = get_client()
    if not client:
        raise HTTPException(status_code=401, detail="用户未登录")

    try:
        result = await client.like_video(bvid=bvid, like=like)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/coin")
async def coin_video(
    bvid: str = Form(...),
    multiply: int = Form(...),
    select_like: str = Form("0")
) -> Dict[str, Any]:
    """投币"""
    client = get_client()
    if not client:
        raise HTTPException(status_code=401, detail="用户未登录")

    try:
        result = await client.coin_video(bvid=bvid, multiply=multiply, select_like=select_like)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/favorite")
async def favorite_video(
    rid: int = Form(...),
    type: int = Form(2),
    add_media_ids: str = Form(""),
    del_media_ids: str = Form("")
) -> Dict[str, Any]:
    """收藏视频"""
    client = get_client()
    if not client:
        raise HTTPException(status_code=401, detail="用户未登录")

    try:
        result = await client.favorite_video(
            rid=rid, type=type,
            add_media_ids=add_media_ids,
            del_media_ids=del_media_ids
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user-info/{mid}")
async def get_user_info(mid: int) -> Dict[str, Any]:
    """获取用户信息"""
    try:
        async with BilibiliClient() as client:
            result = await client.get_user_info_by_mid(mid)
            return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user-stat/{mid}")
async def get_user_stat(mid: int) -> Dict[str, Any]:
    """获取用户统计信息"""
    try:
        async with BilibiliClient() as client:
            result = await client.get_user_stat(mid)
            return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user-videos/{mid}")
async def get_user_videos(
    mid: int,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=50, description="每页数量")
) -> Dict[str, Any]:
    """获取用户投稿视频"""
    try:
        async with BilibiliClient() as client:
            result = await client.get_user_videos(mid, pn=page, ps=page_size)
            return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
