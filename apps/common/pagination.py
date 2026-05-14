"""Pagination class used by every list endpoint.

Adds two things over DRF's default PageNumberPagination:
- `?page_size=...` query param, clamped at 60
- `total_pages` in the response envelope so the frontend doesn't have
  to compute `ceil(count / page_size)` itself.
"""

import math

from rest_framework import pagination
from rest_framework.response import Response


class StandardResultsPagination(pagination.PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 60

    def get_paginated_response(self, data):
        page_size = self.get_page_size(self.request) or self.page_size
        count = self.page.paginator.count
        total_pages = math.ceil(count / page_size) if page_size else 1
        return Response({
            "count": count,
            "total_pages": total_pages,
            "next": self.get_next_link(),
            "previous": self.get_previous_link(),
            "results": data,
        })
