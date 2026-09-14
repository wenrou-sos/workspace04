from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    """默认每页 50 条，允许客户端用 page_size 放大（上限 5000）。"""

    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 5000
