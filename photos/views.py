from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.conf import settings
from .models import Category, Photo
from .forms import CreateUserForm
from django.http import JsonResponse
from html import unescape
from ast import literal_eval
import time
import threading
import cv2 as cv
import os
from imgaug import augmenters as iaa
import numpy as np
import base64

task_complete = False

def selectAugmentations(request):
    if(request.method=="POST"):
        augmentations=request.POST.getlist('augmentations')
        premade=request.POST.getlist('premade')
        
    
        context = {'augmentations': augmentations}
        return render(request, 'photos/photo.html', context)
    return render(request, "photos/augment.html")

def augment(request):
    time.sleep(5)

    # clean up the string from ajax
    augmentations=unescape(request.POST.getlist('augmentations')[0])
    # evaluate the string as list
    augmentations=literal_eval(augmentations)
    augmenters=[]

    for augmentation in augmentations:
        match (augmentation):
            case 'solarize':
                augmenters.append(iaa.Solarize(0.5, threshold=(32, 128)))
                print(augmentation)
            case 'posterize':
                augmenters.append(iaa.Posterize(2))
                print(augmentation)
            case 'translatex':
                augmenters.append(iaa.TranslateX(percent=(-0.2, 0.2)))
                print(augmentation)
            case 'translatey':
                augmenters.append(iaa.TranslateY(percent=(-0.2, 0.2)))
                print(augmentation)
            case 'shearx':
                augmenters.append(iaa.ShearX((-20, 20)))
                print(augmentation)
            case 'sheary':
                augmenters.append(iaa.ShearY((-20, 20)))
                print(augmentation)
            case 'flipx':
                augmenters.append(iaa.Fliplr(0.5))
                print(augmentation)
            case 'flipy':
                augmenters.append(iaa.Flipud(0.5))
                print(augmentation)
            case 'rotate':
                augmenters.append(iaa.Affine(rotate=(-45, 45)))
                print(augmentation)
            case _:
                print("illegal state")

    augmentedPhotos=[]
    photourl=os.path.normpath("..\\static"+"\\images\\tree_FD89IFe.jpg")
    url=os.path.normpath(os.path.join(settings.PROJECT_ROOT, photourl))
    img = cv.imread(url)
    seq = iaa.Sequential(augmenters)
    images=np.array([img, img, img])
    photos=seq(images=images)
    for photo in photos:
        jpgphoto = cv.imencode('.jpg', photo)[1]
        encoded=str(base64.b64encode(jpgphoto), "utf-8")
        augmentedPhotos.append(encoded)
    return JsonResponse({'url': augmentedPhotos[0]})

def registerPage(request):
    form=CreateUserForm()

    if request.method=='POST':
        form = CreateUserForm(request.POST)
        if form.is_valid():
            form.save()

    context={'form':form}

    return render(request, "photos/register.html", context)

def loginPage(request):
    if request.method=="POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return redirect("gallery")

    context={}
    return render(request, "photos/login.html", context)

def logoutUser(request):
    logout(request)
    return redirect('login')

def gallery(request):
    if request.user.is_authenticated==False:
        context = {'page':'home', 'categories': None, 'photos': None, 'user': None}
        return render(request, 'photos/gallery.html', context)
    category = request.GET.get('category')
    categories = Category.objects.all
    if category==None:
        photos = Photo.objects.all
    else:
        photos=Photo.objects.filter(category__name=category)
    context = {'page':'Gallery', 'categories': categories, 'photos': photos, 'user': request.user}
    return render(request, 'photos/gallery.html', context)

def viewPhoto(request, pk):
    augmentedPhotos=[]
    photo = Photo.objects.get(id=pk)
    
    if request.method == 'POST':
        photourl=os.path.normpath("..\\static"+photo.image.url)
        print(photourl)
        url=os.path.normpath(os.path.join(settings.PROJECT_ROOT, photourl))
        img = cv.imread(url)
        seq = iaa.Sequential([
            iaa.TranslateX(percent=(-0.2, 0.2)),
            iaa.ShearX((-20, 20)),
            iaa.ShearY((-20, 20))
        ])
        images=np.array([img, img, img])
        photos=seq(images=images)
        for photo in photos:
            jpgphoto = cv.imencode('.jpg', photo)[1]
            encoded=str(base64.b64encode(jpgphoto), "utf-8")
            augmentedPhotos.append(encoded)


    context = {'photo': photo, 'augmentedPhotos': augmentedPhotos}
    return render(request, 'photos/photo.html', context)

def addPhoto(request):
    categories = Category.objects.all

    if request.method == 'POST':
        data = request.POST
        images =  request.FILES.getlist('images')
        print(images)
        
        if data['category'] != 'null':
            category = Category.objects.get(id=data['category'])
        elif data['category-new'] != '':
            category, created = Category.objects.get_or_create(name = data['category-new'])
        else:
            category = None
        
        for image in images:
            photo=Photo.objects.create(
                category=category,
                description=data['description'],
                image=image
            )
        
        return redirect('gallery')

    context = {'categories' : categories}
    return render(request, 'photos/add.html', context)
