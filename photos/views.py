from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.conf import settings
from .models import Category, Photo
from django import forms
from .forms import CreateUserForm
from django.http import JsonResponse, FileResponse
from html import unescape
from ast import literal_eval
from django.http import HttpResponseBadRequest
from django.views.decorators.http import require_GET
from django.core.files.base import ContentFile
from zipfile import ZipFile
from io import BytesIO
from queue import Queue
from PIL import Image
import glob
import threading
import time
import cv2 as cv
import os, shutil, errno
from imgaug import augmenters as iaa
import numpy as np
import base64
import tempfile





task_complete = False

def selectAugmentations(request):
    context = {'page':'Augment'}
    if(request.method=="POST"):
        augmentations=request.POST.getlist('augmentations')
        premade=request.POST.getlist('premade')
        # if either is empty set to default values
        solarizeRange=[request.POST.get('min0'), request.POST.get('max0')]
        if(not solarizeRange[0] or not solarizeRange[1]):
            solarizeRange=[20, 40]
        print(solarizeRange)
        solarizeRange=[int(each) for each in solarizeRange]
        print(solarizeRange)
        if(premade):
            premade=True
        else:
            premade=False
        context = {'page':'Augment', 'augmentations': augmentations, 'premade':premade}
        return render(request, 'photos/photo.html', context)
    user_path = os.path.join(settings.PROJECT_ROOT, "..", "dynamic/", request.user.username)

    if( not(os.listdir(user_path))):
        print("is empty")
        context['hasDataset']=False

    items = ["0","1","2","3","4","5","6","7","8"]
    context['list']=items
    return render(request, "photos/augment.html", context)

def augment(request):
    premade=request.POST.getlist('premade')[0]
    # clean up the string from ajax
    augmentations=unescape(request.POST.getlist('augmentations')[0])
    # evaluate the string as list
    augmentations=literal_eval(augmentations)
    print(augmentations)
    augmenters=[]
    if(premade=="True"):
        augmenters.append(iaa.RandAugment(n=1, m=9))
    else:
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
                # iaa.Crop(percent=(0, 0.2))
                case 'shearx':
                    augmenters.append(iaa.ShearX((-20, 20))) #degrees
                    print(augmentation)
                case 'sheary':
                    augmenters.append(iaa.ShearY((-20, 20))) #degrees
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

    user_path = os.path.join(settings.PROJECT_ROOT, "..", "dynamic/", request.user.username)
    for subdir, dirs, files in os.walk(user_path):
        for file in files:
            # Create the full file path
            file_path = os.path.join(subdir, file)

            # Check if the file is an image (optional)
            if file.endswith('.jpg') or file.endswith('.png'):
                # Open the image using PIL
                image =np.array( Image.open(file_path))
                

                # Apply the augmentations
                augmented_image = seq.augment_image(image)
                augmented_image_pil = Image.fromarray(augmented_image)
                # Save the augmented image in the same directory
                augmented_file_path = os.path.join(subdir, f"augmented_{file}")
                augmented_image_pil.save(augmented_file_path, format='PNG')
    return JsonResponse({'url': augmentedPhotos[0]})

def registerPage(request):
    form=CreateUserForm()

    if request.method=='POST':
        form = CreateUserForm(request.POST)
        if form.is_valid():
            form.save()
            
            #Creating a folder for each registered user
            new_dir_path = os.path.join(settings.PROJECT_ROOT,'..', 'dynamic', request.POST.get('username'))
            try:
                os.mkdir(new_dir_path)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    #directory already exists
                    pass
                else:
                    print(e)

    context={'page':'Register','form':form}

    return render(request, "photos/register.html", context)

def loginPage(request):
    if request.method=="POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return redirect("gallery")

    context={'page':'Login'}
    return render(request, "photos/login.html", context)

def logoutUser(request):
    logout(request)
    return redirect('gallery')

def gallery(request):
    if request.user.is_authenticated==False:
        context = {'page':'Home', 'categories': None, 'photos': None, 'user': None}
        return render(request, 'photos/gallery.html', context)
    category = request.GET.get('category')
    categories = Category.objects.all
    if category==None:
        photos = Photo.objects.all
    else:
        photos=Photo.objects.filter(category__name=category)
    context = {'page':'Home', 'categories': categories, 'photos': photos, 'user': request.user}
    return render(request, 'photos/gallery.html', context)

def download(request):
    filename = request.GET.get('filename')
    if filename:
        # Return a FileResponse containing the contents of the temporary file
        return FileResponse(open(filename, 'rb'), as_attachment=True, filename='dataset.zip')
    return HttpResponseBadRequest()

def zip_folder_thread(queue, folder_path):
    time.sleep(1)
    zip_file = tempfile.NamedTemporaryFile(delete=False)
    name=zip_file.name
    with ZipFile(zip_file, 'w') as zip_file:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                zip_file.write(file_path, os.path.relpath(file_path, folder_path))
    
    zip_file.close()
    queue.put(name)


def viewPhoto(request):
    context = {'page':'Augment'}
    if request.method == 'POST':
        
        queue = Queue()
        folder_path = os.path.normpath(os.path.join(settings.PROJECT_ROOT, "..", "dynamic/",request.user.username))
        print(folder_path)
        if folder_path:
            # Start the zip process in a new thread
            thread = threading.Thread(target=zip_folder_thread, args=(queue, folder_path,))
            thread.start()
            # Return a JSON response containing the URL to the temporary file
            filename=queue.get()
            print(filename)
            return JsonResponse({'url': filename})
    return render(request, 'photos/photo.html', context)
    
    # folder_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test')
    # if not os.path.exists(folder_path):
    #     return HttpResponse('Folder not found')

    # file_name = 'my_folder.zip'
    # zip_buffer = BytesIO()

    # with ZipFile(zip_buffer, 'w') as zip_file:
    #     for root, dirs, files in os.walk(folder_path):
    #         for file in files:
    #             file_path = os.path.join(root, file)
    #             zip_file.write(file_path, os.path.relpath(file_path, folder_path))

    # zip_buffer.seek(0)
    # # Get the size of the zip file
    # zip_size = zip_buffer.getbuffer().nbytes

    # # Create an HTTP response with the zip file as an attachment
    # response = HttpResponse(zip_buffer, content_type='application/zip')
    # response['Content-Disposition'] = 'attachment; filename="{}"'.format(file_name)

    # # Set the Content-Length header based on the size of the zip file
    # response['Content-Length'] = str(zip_size)
    
    
    # print("here")
    # # Return the HTTP response to the user
    # return response

    #old photo
    #augmentedPhotos=[]
    #photo = Photo.objects.get(id=pk)
    # if request.method == 'POST':
    #     photourl=os.path.normpath("..\\static"+photo.image.url)
    #     print(photourl)
    #     url=os.path.normpath(os.path.join(settings.PROJECT_ROOT, photourl))
    #     img = cv.imread(url)
    #     seq = iaa.Sequential([
    #         iaa.TranslateX(percent=(-0.2, 0.2)),
    #         iaa.ShearX((-20, 20)),
    #         iaa.ShearY((-20, 20))
    #     ])
    #     images=np.array([img, img, img])
    #     photos=seq(images=images)
    #     for photo in photos:
    #         jpgphoto = cv.imencode('.jpg', photo)[1]
    #         encoded=str(base64.b64encode(jpgphoto), "utf-8")
    #         augmentedPhotos.append(encoded)


    # context = {'photo': photo, 'augmentedPhotos': augmentedPhotos}
    # return render(request, 'photos/photo.html', context)

def unzip_file(zip_file_path, extract_dir):
    with ZipFile(zip_file_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)



def addPhoto(request):
    user_path = os.path.join(settings.PROJECT_ROOT, "..", "dynamic/", request.user.username)
    context = {'page':'Upload'}
    if request.method == 'POST' and request.FILES.get('zip_file'):
        if (request.user.is_authenticated):
            if(os.listdir(user_path)):
                # deletes existing dataset
                shutil.rmtree(user_path)
                # creates the folder again
                try:
                        os.mkdir(user_path)
                except OSError as e:
                    if e.errno != errno.EEXIST:
                        #directory already exists
                        pass
                    else:
                        print(e)
            
            zip_file = request.FILES['zip_file']
            with ZipFile(zip_file, 'r') as zip_ref:
                zip_ref.extractall(user_path)

            

            context['success']=True
        return render(request, 'photos/add.html', context)
    
    if(os.listdir(user_path)):
        context['hasDataset']=True
    
    return render(request, 'photos/add.html', context)

    
    



    # WIP
    # if request.method == 'POST':
    #     form = request.POST
    #     directory_name = form['dir_name']
    #     print(directory_name)
    #     # os.mkdir(os.path.join(settings.PROJECT_ROOT, "..", "dynamic/", directory_name))
    #     files =  request.FILES.getlist('images')
    #     print(files)
    # context = {'page':'add'}
    # return render(request, 'photos/add.html', context)



    # categories = Category.objects.all

    # if request.method == 'POST':
    #     data = request.POST
    #     images =  request.FILES.getlist('images')
    #     print(images)
        
    #     if data['category'] != 'null':
    #         category = Category.objects.get(id=data['category'])
    #     elif data['category-new'] != '':
    #         category, created = Category.objects.get_or_create(name = data['category-new'])
    #     else:
    #         category = None
        
    #     for image in images:
    #         photo=Photo.objects.create(
    #             category=category,
    #             description=data['description'],
    #             image=image
    #         )
        
    #     return redirect('gallery')

    # context = {'page':'add', 'categories' : categories}
    # return render(request, 'photos/add.html', context)
