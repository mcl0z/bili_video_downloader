from fastapi import APIRouter, HTTPException, Form
from typing import Dict, Any, Optional
from ..bilibili.client import BilibiliClient
from .auth import get_client

router = APIRouter(prefix="/comment", tags=["评论"])


@router.get("/list")
async def get_comments(
    type: int = 1,
    oid: int = ...,
    pn: int = 1,
    ps: int = 20,
    sort: int = 0
) -> Dict[str, Any]:
    """获取评论列表"""
    try:
        # 优先使用已登录的客户端，如果没有则创建临时客户端
        client = get_client()
        if client:
            result = await client.get_comments(type=type, oid=oid, pn=pn, ps=ps, sort=sort)
        else:
            # 创建临时客户端实例
            async with BilibiliClient() as temp_client:
                result = await temp_client.get_comments(type=type, oid=oid, pn=pn, ps=ps, sort=sort)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/add")
async def add_comment(
    type: int = Form(1),
    oid: int = Form(...),
    message: str = Form(...),
    root: int = Form(0),
    parent: int = Form(0),
    plat: int = Form(1)
) -> Dict[str, Any]:
    """发表评论"""
    client = get_client()
    if not client:
        raise HTTPException(status_code=401, detail="用户未登录")
    
    try:
        result = await client.add_comment(
            type=type, oid=oid, message=message, 
            root=root, parent=parent, plat=plat
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/like")
async def like_comment(
    type: int = Form(1),
    oid: int = Form(...),
    rpid: int = Form(...),
    action: int = Form(...)
) -> Dict[str, Any]:
    """点赞评论"""
    client = get_client()
    if not client:
        raise HTTPException(status_code=401, detail="用户未登录")
    
    try:
        result = await client.like_comment(type=type, oid=oid, rpid=rpid, action=action)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
