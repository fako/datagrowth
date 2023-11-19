from copy import deepcopy

from django.shortcuts import Http404
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from project.entities.constants import EntityStates, SEED_DEFAULTS
from project.entities.generators import seed_generator


class EntityListAPIView(APIView):

    permission_classes = (AllowAny,)

    def get(self, request, entity):
        if entity not in SEED_DEFAULTS:
            raise Http404(f"Entity doesn't exist: {entity}")
        # Generate the basic seeds
        size = int(request.GET.get("size", 20))
        seeds = list(seed_generator(entity, size))
        # import json; print(json.dumps(seeds, indent=4))

        # Delete some seeds if necessary
        deletes = int(request.GET.get("deletes", 0))
        if deletes:
            for ix, seed in enumerate(seeds):
                if deletes < 0 or not ix % deletes:
                    seed["state"] = EntityStates.DELETED

        # Generate some nested seeds if required and divide those among the main generated seeds
        nested_entity = request.GET.get("nested", None)
        if nested_entity:
            nested_seeds = list(seed_generator(nested_entity, size))
            for ix, seed in enumerate(seeds):
                nested = []
                nested_length = ix % 3
                for _ in range(0, nested_length):
                    nested.append(nested_seeds.pop(0))
                seed[f"{nested_entity}s"] = deepcopy(nested) if seed["state"] != EntityStates.DELETED else []

        # Return the paginator
        paginator = PageNumberPagination()
        paginator.page_size_query_param = "page_size"
        paginator.page_size = 10
        page_data = paginator.paginate_queryset(seeds, request, view=self)
        if not page_data:
            return paginator.get_paginated_response(seeds)
        return paginator.get_paginated_response(data=page_data)


class EntityIdListAPIView(APIView):

    permission_classes = (AllowAny,)

    def get(self, request, entity):
        size = int(request.GET.get("size", 20))
        seeds = list(seed_generator(entity, size))
        delete_ids = []

        deletes = int(request.GET.get("deletes", 0))
        if deletes:
            for ix, seed in enumerate(seeds):
                if deletes < 0 or not ix % deletes:
                    delete_ids.append(seed["id"])

        return Response([{"id": obj["id"]} for obj in seeds if obj["id"] not in delete_ids])


class EntityDetailAPIView(APIView):

    permission_classes = (AllowAny,)

    def get(self, request, pk, entity):
        size = int(request.GET.get("size", 20))
        seeds = list(seed_generator(entity, size))
        try:
            return Response(next((obj for obj in seeds if str(obj["id"]) == pk)))
        except StopIteration:
            raise Http404(f"Object with primary key not found: {pk}")
