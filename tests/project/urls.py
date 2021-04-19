from django.urls import path, include
from django.contrib import admin

from datatypes.urls import urlpatterns as datatypes_urlpatterns


api_v1_patterns = [
    path("datatypes/", include((datatypes_urlpatterns, "datatypes",)))
]

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include((api_v1_patterns, "v1",)))
]
