from django.conf import settings
from rest_framework.pagination import _positive_int, PageNumberPagination
from rest_framework.response import Response


class IncludePageSizePagination(PageNumberPagination):
    page_size_query_param = "page_size"
    max_page_size = settings.MAX_PAGE_SIZE

    extra_metadata = {}

    def get_page_size(self, request):
        if request.accepted_renderer.format == "csv":
            self.max_page_size = settings.CSV_MAX_PAGE_SIZE

        if self.page_size_query_param:
            try:
                return _positive_int(request.query_params[self.page_size_query_param], strict=True, cutoff=self.max_page_size)
            except (KeyError, ValueError):
                pass

        return self.page_size

    def add_extra_metadata(self, extra_metadata: dict):
        self.extra_metadata.update(extra_metadata)

    def get_paginated_response(self, data):

        response = Response(
            {
                "meta": {
                    "total_results": self.page.paginator.count,
                    "total_pages": self.page.paginator.num_pages,
                    "page_size": self.get_page_size(self.request),
                    "page": self.request.query_params.get(self.page_query_param, 1),
                    "links": {"next": self.get_next_link(), "previous": self.get_previous_link()},
                    **self.extra_metadata,
                },
                "results": data,
            }
        )
        # reset extra metadata for paginator
        self.extra_metadata = {}
        return response
