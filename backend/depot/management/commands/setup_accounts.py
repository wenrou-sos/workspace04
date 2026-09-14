"""初始化演示账号与岗位授权（幂等）。

账号清单（密码见各账号，均为演示用弱口令）：
  admin / admin123        系统管理员（超级用户）
  director / director123  库管主任（赵国栋）：全仓业务、删除、盘点调账
  保管员（仅本人仓房日常业务，不能删除/调账/安排熏蒸）：
    zhangjg 张建国→P01  lixy 李秀英→P02  wanght 王海涛→P03
    chenlh 陈丽华→P04   liuzq 刘志强→X01  zhaom  赵敏→X02
    sunw   孙伟→L01    zhouf 周芳→L02
    密码均为 keeper123
  viewer / viewer123      只读用户：全仓只读、看板
"""
from django.contrib.auth.models import User

from depot.models import Granary, UserProfile

# 仓号 → (用户名, 姓名)
KEEPERS = {
    "P01": ("zhangjg", "张建国"),
    "P02": ("lixy", "李秀英"),
    "P03": ("wanght", "王海涛"),
    "P04": ("chenlh", "陈丽华"),
    "X01": ("liuzq", "刘志强"),
    "X02": ("zhaom", "赵敏"),
    "L01": ("sunw", "孙伟"),
    "L02": ("zhouf", "周芳"),
}


def _get_or_create_user(username, password, name, role, is_super=False):
    user, created = User.objects.get_or_create(
        username=username,
        defaults={"is_staff": is_super, "is_superuser": is_super, "is_active": True,
                  "first_name": name},
    )
    if created:
        user.set_password(password)
        user.save()
    if not user.has_usable_password() or created:
        user.set_password(password)
        user.save()
    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.role = role
    profile.display_name = name
    profile.save()
    return user, profile


def ensure_accounts(granary_map=None):
    """创建/校正全部演示账号；granary_map 给定时为保管员分配管辖仓房。

    返回 {"director": user, "viewers":[...], "keepers": {仓号: user}}。
    """
    admin_user, admin_profile = _get_or_create_user(
        "admin", "admin123", "系统管理员", UserProfile.Role.ADMIN, is_super=True
    )
    admin_user.is_staff = True
    admin_user.is_superuser = True
    admin_user.save()

    director, _ = _get_or_create_user(
        "director", "director123", "赵国栋", UserProfile.Role.DIRECTOR
    )
    _get_or_create_user("viewer", "viewer123", "访客", UserProfile.Role.VIEWER)

    keepers = {}
    for code, (uname, name) in KEEPERS.items():
        user, profile = _get_or_create_user(uname, "keeper123", name, UserProfile.Role.KEEPER)
        keepers[code] = user
        if granary_map and code in granary_map:
            profile.granaries.set([granary_map[code]])

    return {"admin": admin_user, "director": director, "keepers": keepers}
