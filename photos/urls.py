from django.urls import path
from . import views

urlpatterns = [
    path('',views.gallery, name='gallery'),
    path('photo/<str:pk>/',views.viewPhoto, name='photo'),
    path('add/',views.addPhoto, name='add'),
    path('register/', views.registerPage, name='register'),
    path('login/', views.loginPage, name='login'),
    path('logout/', views.logoutUser, name='logout'),
]