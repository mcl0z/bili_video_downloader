from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os
from .api import auth, video, comment

# 创建FastAPI应用
app = FastAPI(
    title="Bilibili 客户端 API",
    description="基于Python的Bilibili客户端后端API",
    version="1.0.0"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册API路由
app.include_router(auth.router, prefix="/api")
app.include_router(video.router, prefix="/api")
app.include_router(comment.router, prefix="/api")

# 应用启动时自动加载保存的cookies
@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    print("正在启动Bilibili客户端...")
    auth.init_client_from_saved_cookies()

# 静态文件服务
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=os.path.join(frontend_path, "static")), name="static")

@app.get("/")
async def read_root():
    """主页"""
    frontend_index = os.path.join(frontend_path, "templates", "index.html")
    if os.path.exists(frontend_index):
        return FileResponse(frontend_index)
    return {"message": "Bilibili 客户端 API", "version": "1.0.0"}

@app.get("/video")
async def video_page():
    """视频播放页面"""
    video_page_path = os.path.join(frontend_path, "templates", "video.html")
    print(f"查找视频页面: {video_page_path}")
    print(f"文件是否存在: {os.path.exists(video_page_path)}")

    if os.path.exists(video_page_path):
        return FileResponse(video_page_path)

    # 如果路径不存在，尝试其他可能的路径
    alternative_path = os.path.join(os.getcwd(), "frontend", "templates", "video.html")
    print(f"尝试备用路径: {alternative_path}")
    print(f"备用路径是否存在: {os.path.exists(alternative_path)}")

    if os.path.exists(alternative_path):
        return FileResponse(alternative_path)

    return {"message": "视频页面未找到", "error": "404", "searched_paths": [video_page_path, alternative_path]}

@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "message": "服务运行正常"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
