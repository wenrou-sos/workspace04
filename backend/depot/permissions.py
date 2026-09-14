"""岗位权限与仓房范围控制。

角色：
- admin    系统管理员：全部权限
- director 库管主任：全部业务权限 + 删除 + 盘点调账（审核）
- keeper   保管员：仅本人管辖仓房的日常业务，不能删除、不能调账
- viewer   只读用户：全站只读（含看板）
"""
from rest_framework.permissions import BasePermission

from depot.models import UserProfile


def get_profile(user):
    if not user or not user.is_authenticated:
        return None
    return getattr(user, "profile", None)


def is_admin(user):
    p = get_profile(user)
    return bool(p and (user.is_superuser or p.role == UserProfile.Role.ADMIN))


def is_director(user):
    p = get_profile(user)
    return bool(p and p.role in {UserProfile.Role.ADMIN, UserProfile.Role.DIRECTOR})


def is_keeper(user):
    p = get_profile(user)
    return bool(p and p.role == UserProfile.Role.KEEPER)


def can_access_granary(user, granary):
    p = get_profile(user)
    if not p:
        return False
    return p.can_access_granary(granary)


class DepotPermission(BasePermission):
    """可按 ViewSet 配置的岗位权限。

    用法（在 ViewSet 上设置属性）：
      create_roles / update_roles / delete_roles: 允许的角色集合
      scoped_create: True 时创建动作还要校验目标仓房在管辖范围内
      action_roles: {'advance': {'director','keeper',...}, ...}
    """

    message = "当前岗位无权执行该操作"

    DEFAULT_WRITERS = {"admin", "director", "keeper"}

    def _allowed_roles(self, view, kind):
        attr = f"{kind}_roles"
        value = getattr(view, attr, None)
        if value is not None:
            return set(value)
        if kind in {"create", "update"}:
            return set(self.DEFAULT_WRITERS)
        if kind == "delete":
            return {"admin", "director"}
        return set(self.DEFAULT_WRITERS)

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        profile = get_profile(user)
        if not profile:
            return False
        role = profile.role
        if is_admin(user):
            role = "admin"

        if request.method in ("GET", "HEAD", "OPTIONS"):
            read_roles = getattr(view, "read_roles", None)
            if read_roles is not None and role not in read_roles:
                self.message = "当前岗位无权查看该模块"
                return False
            return True  # 已登录即可读，保管员的数据范围由 queryset 过滤

        action = getattr(view, "action", None)
        action_roles = getattr(view, "action_roles", {})
        if action in action_roles:
            if role not in action_roles[action]:
                self.message = f"该操作仅限：{'、'.join(sorted(action_roles[action]))}"
                return False
        elif request.method == "POST":
            if role not in self._allowed_roles(view, "create"):
                self.message = "当前岗位无新增权限"
                return False
        elif request.method in ("PUT", "PATCH"):
            if role not in self._allowed_roles(view, "update"):
                self.message = "当前岗位无修改权限"
                return False
        elif request.method == "DELETE":
            if role not in self._allowed_roles(view, "delete"):
                self.message = "删除仅限系统管理员或库管主任"
                return False

        # 仅在标准新增动作上校验请求体里的目标仓房范围；
        # advance / generate_items 等自定义动作由视图内部按对象/明细自行过滤
        if (
            request.method == "POST"
            and action in (None, "create")
            and getattr(view, "scoped_create", False)
            and role == "keeper"
        ):
            granary = view.extract_granary(request.data)
            if granary is None or not can_access_granary(user, granary):
                self.message = "无权操作非本人管辖的仓房"
                return False
        return True

    def has_object_permission(self, request, view, obj):
        user = request.user
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        if is_admin(user) or get_profile(user).role == UserProfile.Role.DIRECTOR:
            return True
        # 保管员只能操作自己管辖仓房的对象
        granary = view.obj_granary(obj) if hasattr(view, "obj_granary") else None
        if granary is not None and not can_access_granary(user, granary):
            self.message = "该数据属于其他保管员负责的仓房，无权操作"
            return False
        return True
