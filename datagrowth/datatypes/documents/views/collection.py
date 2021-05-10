from django.shortcuts import Http404

from rest_framework import serializers
from rest_framework.response import Response

from .content import ContentView, ContentPagination


class CollectionBaseSerializer(serializers.ModelSerializer):

    default_fields = ("id", "name", "created_at", "modified_at", "referee", "identifier",)


class CollectionBaseContentView(ContentView):
    """
    A Collection is a list of Documents
    """
    pagination_class = ContentPagination

    def retrieve(self, request, *args, **kwargs):
        """
        Will return a list of content which can be paginated.

        :param request: Django request
        :return: Response
        """
        if request.object is None:
            raise Http404("Not found")

        page = self.paginate_queryset(request.object.documents.all())
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(request.object.content, many=True)
        return Response(serializer.data)
