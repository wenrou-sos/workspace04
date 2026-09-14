"""根路由：管理后台 + REST API。"""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("depot.urls")),
]
