from django.urls import path, include
from django.contrib import admin

from datatypes.urls import urlpatterns as datatypes_urlpatterns
from project.entities.views import EntityListAPIView, EntityIdListAPIView, EntityDetailAPIView


api_v1_patterns = [
    path("datatypes/", include((datatypes_urlpatterns, "datatypes",)))
]

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include((api_v1_patterns, "v1",))),

    path('entities/<str:entity>/ids/', EntityIdListAPIView.as_view(), name="entity-ids"),
    path('entities/<str:entity>/<str:pk>/', EntityDetailAPIView.as_view(), name="entity-detail"),
    path('entities/<str:entity>/', EntityListAPIView.as_view(), name="entities"),
]
