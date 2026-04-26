from packages.shared.config import get_settings


def verify_verification_token(payload: dict) -> bool:
    """第一版只做 Verification Token 校验。

    注意：如果你在飞书后台启用了 Encrypt Key 加密策略，需要增加解密和签名校验。
    """
    settings = get_settings()
    expected = settings.feishu_verification_token
    if not expected:
        return True

    token = payload.get("token") or payload.get("header", {}).get("token")
    return token == expected
