from django.urls import path
from . import views

urlpatterns = [
    path('',views.home, name='home'),
    path('zip/', views.zipDataset, name='zip'),
    path('upload/',views.uploadDataset, name='upload'),
    path('register/', views.registerPage, name='register'),
    path('login/', views.loginPage, name='login'),
    path('logout/', views.logoutUser, name='logout'),
    path('augment/', views.selectAugmentations, name='augment'),
    path('augmentDataset/', views.augmentDataset, name='augmentDataset'),
    path('download/', views.download, name='download'),
    path('delete/', views.deleteDataset, name='delete'),
]