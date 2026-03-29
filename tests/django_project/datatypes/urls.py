from django.urls import path

from datatypes import views


app_name = "datatypes"
urlpatterns = [
    path('data/collection/<int:pk>/content/', views.CollectionContentView.as_view(), name="collection-content"),
    path('data/collection/<int:pk>/', views.CollectionView.as_view(), name="collection"),
    path('data/document/<int:pk>/content/', views.DocumentContentView.as_view(), name="document-content"),
    path('data/document/<int:pk>/', views.DocumentView.as_view(), name="document"),
]
