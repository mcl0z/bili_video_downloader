from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class VideoOwner(BaseModel):
    """视频UP主信息"""
    mid: int
    name: str
    face: str


class VideoStat(BaseModel):
    """视频统计信息"""
    view: int = 0
    danmaku: int = 0
    reply: int = 0
    favorite: int = 0
    coin: int = 0
    share: int = 0
    like: int = 0
    dislike: int = 0


class VideoDimension(BaseModel):
    """视频分辨率信息"""
    width: int
    height: int
    rotate: int


class VideoPage(BaseModel):
    """视频分P信息"""
    cid: int
    page: int
    from_: str = ""
    part: str
    duration: int
    vid: str = ""
    weblink: str = ""
    dimension: VideoDimension


class VideoInfo(BaseModel):
    """视频基本信息"""
    bvid: str
    aid: int
    videos: int
    tid: int
    tname: str
    copyright: int
    pic: str
    title: str
    pubdate: int
    ctime: int
    desc: str
    duration: int
    owner: VideoOwner
    stat: VideoStat
    dynamic: str = ""
    cid: int
    dimension: VideoDimension
    pages: List[VideoPage] = []


class SearchResult(BaseModel):
    """搜索结果"""
    type: str
    id: int
    author: str
    title: str
    description: str
    pic: str
    duration: str = ""
    view: int = 0
    danmaku: int = 0
    pubdate: int = 0


class SearchResponse(BaseModel):
    """搜索响应"""
    seid: str
    page: int
    pagesize: int
    numResults: int
    numPages: int
    result: List[SearchResult] = []


class UserInfo(BaseModel):
    """用户信息"""
    isLogin: bool
    mid: Optional[int] = None
    uname: Optional[str] = None
    face: Optional[str] = None
    level_info: Optional[dict] = None
    money: Optional[float] = None
    vipStatus: Optional[int] = None
    vipType: Optional[int] = None
