from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from ..bilibili.auth import BilibiliAuth
from ..bilibili.client import BilibiliClient
from ..utils.cookie_manager import cookie_manager

router = APIRouter(prefix="/auth", tags=["认证"])

# 全局认证实例
auth_instance = None
client_instance = None


@router.get("/qr-login")
async def get_qr_login() -> Dict[str, Any]:
    """获取二维码登录"""
    global auth_instance
    
    try:
        auth_instance = BilibiliAuth()
        result = await auth_instance.login_with_qr()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/qr-status/{qrcode_key}")
async def check_qr_status(qrcode_key: str) -> Dict[str, Any]:
    """检查二维码扫描状态"""
    global auth_instance, client_instance
    
    if not auth_instance:
        raise HTTPException(status_code=400, detail="请先获取二维码")
    
    try:
        result = await auth_instance.check_qr_status(qrcode_key)
        
        # 如果登录成功，设置客户端cookies并保存
        if result['status'] == 'success' and 'cookies' in result:
            if not client_instance:
                client_instance = BilibiliClient()
            client_instance.set_cookies(result['cookies'])

            # 获取用户信息并保存cookies
            try:
                user_info_response = await client_instance.get_user_info()
                if user_info_response.get('code') == 0:
                    user_data = user_info_response.get('data', {})
                    user_id = str(user_data.get('mid', 'unknown'))

                    # 保存cookies和用户信息
                    cookie_manager.save_cookies(user_id, result['cookies'], user_data)
                    print(f"已保存用户 {user_data.get('uname', user_id)} 的登录信息")
            except Exception as e:
                print(f"保存用户信息失败: {e}")

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user-info")
async def get_user_info() -> Dict[str, Any]:
    """获取用户信息"""
    global client_instance
    
    if not client_instance:
        raise HTTPException(status_code=401, detail="用户未登录")
    
    try:
        result = await client_instance.get_user_info()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/logout")
async def logout() -> Dict[str, Any]:
    """登出"""
    global auth_instance, client_instance
    
    try:
        if auth_instance:
            await auth_instance.__aexit__(None, None, None)
            auth_instance = None
        
        if client_instance:
            await client_instance.__aexit__(None, None, None)
            client_instance = None
        
        return {"status": "success", "message": "登出成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/saved-users")
async def get_saved_users() -> Dict[str, Any]:
    """获取已保存的用户列表"""
    try:
        users = cookie_manager.get_all_users()
        return {"code": 0, "data": users}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/load-user/{user_id}")
async def load_saved_user(user_id: str) -> Dict[str, Any]:
    """加载已保存的用户"""
    global client_instance

    try:
        cookies = cookie_manager.get_cookies(user_id)
        user_info = cookie_manager.get_user_info(user_id)

        if not cookies:
            raise HTTPException(status_code=404, detail="用户不存在或cookies已过期")

        # 创建客户端并设置cookies
        if not client_instance:
            client_instance = BilibiliClient()
        client_instance.set_cookies(cookies)

        # 验证cookies是否仍然有效
        user_info_response = await client_instance.get_user_info()
        if user_info_response.get('code') != 0 or not user_info_response.get('data', {}).get('isLogin'):
            # cookies无效，删除保存的数据
            cookie_manager.remove_cookies(user_id)
            client_instance = None
            raise HTTPException(status_code=401, detail="用户登录已过期")

        return {
            "code": 0,
            "message": "用户加载成功",
            "data": user_info_response.get('data', {})
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/saved-user/{user_id}")
async def remove_saved_user(user_id: str) -> Dict[str, Any]:
    """删除已保存的用户"""
    try:
        success = cookie_manager.remove_cookies(user_id)
        if success:
            return {"code": 0, "message": "用户删除成功"}
        else:
            raise HTTPException(status_code=404, detail="用户不存在")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def get_client() -> BilibiliClient:
    """获取客户端实例"""
    global client_instance
    return client_instance


def init_client_from_saved_cookies():
    """从保存的cookies初始化客户端"""
    global client_instance

    try:
        users = cookie_manager.get_all_users()
        if users:
            # 使用最近保存的用户
            latest_user = max(users.items(), key=lambda x: x[1]['saved_time'])
            user_id, user_data = latest_user

            cookies = cookie_manager.get_cookies(user_id)
            if cookies:
                client_instance = BilibiliClient()
                client_instance.set_cookies(cookies)
                print(f"已自动加载用户 {user_data['user_info'].get('uname', user_id)} 的登录信息")
                return True
    except Exception as e:
        print(f"自动加载用户失败: {e}")

    return False
