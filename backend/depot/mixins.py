from django.db.models import ProtectedError, RestrictedError
from rest_framework import status
from rest_framework.response import Response


class ProtectedDeleteMixin:
    """删除被外键引用的对象时，返回 409 与中文引用说明，而不是 500。"""

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            self.perform_destroy(instance)
        except (ProtectedError, RestrictedError) as exc:
            refs = getattr(exc, "protected_objects", None) or getattr(exc, "restricted_objects", [])
            names = sorted({type(obj)._meta.verbose_name for obj in refs})
            detail = f"「{instance}」已被{'、'.join(names)}引用，不能直接删除，请先清理相关业务数据。"
            return Response({"detail": detail}, status=status.HTTP_409_CONFLICT)
        return Response(status=status.HTTP_204_NO_CONTENT)
