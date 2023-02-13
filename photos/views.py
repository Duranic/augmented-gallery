from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.conf import settings
from .models import Category, Photo
from .forms import CreateUserForm
import cv2 as cv
import os
from imgaug import augmenters as iaa
import numpy as np
import base64

def selectAugmentations(request):
    if(request.method=="POST"):
        augmentations=request.POST.getlist('augmentations')
        augmenters=[]
        for augmentation in augmentations:
            match (augmentation):
                case 'solarize':
                    print("selected solarize")
                case 'posterize':
                    print("selected posterize")
                case 'translatex':
                    print("selected translatex")
                case 'translatey':
                    print("selected translatey")
                case 'shearx':
                    print("selected shearx")
                case 'sheary':
                    print("selected sheary")
                case 'flipx':
                    print("selected flipx")
                case 'flipy':
                    print("selected flipy")
                case 'rotate':
                    print("selected rotate")
                case _:
                    print("illegal state")
    return render(request, "photos/augment.html")

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
        context = {'categories': None, 'photos': None, 'user': None}
        return render(request, 'photos/gallery.html', context)
    category = request.GET.get('category')
    categories = Category.objects.all
    if category==None:
        photos = Photo.objects.all
    else:
        photos=Photo.objects.filter(category__name=category)
    context = {'categories': categories, 'photos': photos, 'user': request.user}
    return render(request, 'photos/gallery.html', context)

def viewPhoto(request, pk):
    augmentedPhotos=[]
    print(len(augmentedPhotos))
    photo = Photo.objects.get(id=pk)
    
    if request.method == 'POST':
        photourl=os.path.normpath("..\\static"+photo.image.url)
        url=os.path.normpath(os.path.join(settings.PROJECT_ROOT, photourl))
        img = cv.imread(url)
        seq = iaa.Sequential([
            iaa.Crop(px=(0, 100)), # crop images from each side by 0 to 16px (randomly chosen)
            iaa.Fliplr(0.7), # horizontally flip 50% of the images
            iaa.GaussianBlur(sigma=(0, 3.0)) # blur images with a sigma of 0 to 3.0
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
