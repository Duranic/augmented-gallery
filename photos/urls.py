from django.urls import path
from . import views

urlpatterns = [
    path('',views.gallery, name='gallery'),
    path('photo/', views.viewPhoto, name='photo'),
    path('add/',views.addPhoto, name='add'),
    path('register/', views.registerPage, name='register'),
    path('login/', views.loginPage, name='login'),
    path('logout/', views.logoutUser, name='logout'),
    path('augment/', views.selectAugmentations, name='augment'),
    path('process_image/', views.augment, name='process_image'),
    path('download/', views.download, name='download'),
    path('delete/', views.deleteDataset, name='delete'),
]