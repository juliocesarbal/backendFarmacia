"""Paginacion estandar: 50 por pagina, configurable via ?page_size= (max 200)."""
from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200
