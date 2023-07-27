from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .models import Dataset
from django.conf import settings
from .forms import CreateUserForm, UserForm
from django.http import JsonResponse, FileResponse, HttpResponseBadRequest, HttpResponse
from html import unescape
from ast import literal_eval
from django.core.files.base import ContentFile
from zipfile import ZipFile
from queue import Queue
from PIL import Image
import threading
import os, shutil
from imgaug import augmenters as iaa
import numpy as np
import tempfile


def home(request):
    if request.user.is_authenticated==False:
        context = {'page':'Home'}
        return render(request, 'photos/index.html', context)
    
    user = User.objects.get(username=request.user)
    try:
        dataset = user.dataset  # 'dataset' is the related name defined in the OneToOneField
        datasetName = dataset.name
        creationDate = dataset.creationDate
    except Dataset.DoesNotExist:
        # The dataset does not exist for this user
        datasetName = None
        creationDate = None
    
    context = {'page':'Home', 'creationDate': creationDate, 'datasetName': datasetName}
    return render(request, 'photos/index.html', context)


def registerPage(request):
    form=CreateUserForm()

    if request.method=='POST':
        form = CreateUserForm(request.POST)
        if form.is_valid():
            form.save()
            
            #Creating folders for each registered user
            dataset_path = os.path.join(settings.MEDIA_ROOT, request.POST.get('username'), "dataset")
            augmented_path = os.path.join(settings.MEDIA_ROOT, request.POST.get('username'), "augmented")
            temp_path = os.path.join(settings.MEDIA_ROOT, request.POST.get('username'), "temp")
            try:
                os.makedirs(dataset_path)
                os.makedirs(augmented_path)
                os.makedirs(temp_path)
            except Exception as e:
                print(e)
                return HttpResponse('Something went wrong')
            
            user = authenticate(request, username=request.POST.get('username'), password=request.POST.get('password1'))
        
            if user is not None:
                login(request, user)
                return redirect("home")

    context={'page':'Register','form':form}

    return render(request, "photos/register.html", context)


def loginPage(request):
    form=UserForm()
    if request.method=="POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return redirect("home")
        else:
            context={'page':'Login', 'error_message': 'Username or password entered was incorrect', 'form': form}
            return render(request, "photos/login.html", context)

    context={'page':'Login', 'form': form}
    return render(request, "photos/login.html", context)


def logoutUser(request):
    logout(request)
    return redirect("home")


@login_required
def uploadDataset(request):
    user = User.objects.get(username=request.user)
    try:
        dataset = user.dataset
    except Dataset.DoesNotExist:
        dataset = None
    
    context = {'page':'Upload'}
    if (request.method == 'POST' and request.FILES.get('zip_file')):
        username = request.user.username
        user_path = os.path.join(settings.MEDIA_ROOT, username)
        dataset_path = os.path.join(settings.MEDIA_ROOT, username, "dataset")
        augmented_path = os.path.join(settings.MEDIA_ROOT, username, "augmented")
        temp_path = os.path.join(settings.MEDIA_ROOT, username, "temp")
        
        if (not os.path.exists(user_path)):
            try:
                os.makedirs(dataset_path)
                os.makedirs(augmented_path)
                os.makedirs(temp_path)
            except Exception as e:
                print(e)
                return HttpResponse('Something went wrong')

        # Delete the dataset if it exists
        if(os.listdir(dataset_path)):
            try:
                    # deletes existing dataset
                    shutil.rmtree(dataset_path)
                    # creates the folder again
                    os.mkdir(dataset_path)
            except Exception as e:
                    print(e)
                    return JsonResponse({"message": "Unable to delete existing dataset, please try again"})
        if dataset:
            dataset.delete()
        
        zip_file = request.FILES['zip_file']
         
        try:
            with ZipFile(zip_file, 'r') as zip_ref:
                zip_ref.extractall(dataset_path)
        except Exception as e:
            print(e)
            # return JsonResponse({"message": "Unable to extract .zip file. Check if you uploaded a valid file."})
            return JsonResponse({"error": "Unable to extract .zip file. Check if you uploaded a valid file."}, status=500)

        new_dataset = Dataset(user=user, name=zip_file)
        new_dataset.save()   
            
        return JsonResponse({"message": "File uploaded successfully!"})
    
    if(dataset):
        context['hasDataset']=True
    
    return render(request, 'photos/upload.html', context)



@login_required
def selectAugmentations(request):
    context = {'page':'Augment'}
    if(request.method=="POST"):
        augmentations=request.POST.getlist('augmentations')
        premade=request.POST.getlist('premade')
        
        # get the appropriate values for every augmentation
        solarizeRange=(request.POST.get('min0'), request.POST.get('max0'))
        posterizeRange=request.POST.get('min1')
        translatexRange=(request.POST.get('min2'), request.POST.get('max2'))
        translateyRange=(request.POST.get('min3'), request.POST.get('max3'))
        shearxRange=(request.POST.get('min4'), request.POST.get('max4'))
        shearyRange=(request.POST.get('min5'), request.POST.get('max5'))
        rotateRange=(request.POST.get('min8'), request.POST.get('max8'))
        randAugment=(request.POST.get('min9'), request.POST.get('max9'))

        numberOfImages=request.POST.get('imageRange')

        # if either is empty set to default values
        if(not solarizeRange[0] or not solarizeRange[1]):
            solarizeRange=(32, 128)
        
        if(not posterizeRange):
            posterizeRange=3

        if(not translatexRange[0] or not translatexRange[1]):
            translatexRange=(-20, 20)

        if(not translateyRange[0] or not translateyRange[1]):
            translateyRange=(-20, 20)

        if(not shearxRange[0] or not shearxRange[1]):
            shearxRange=(-20, 20)

        if(not shearyRange[0] or not shearyRange[1]):
            shearyRange=(-20, 20)

        if(not rotateRange[0] or not rotateRange[1]):
            rotateRange=(-45, 45)
        
        if(not randAugment[0] or not randAugment[1]):
            randAugment=(2, 9)

        solarizeRange=(int(solarizeRange[0]), int(solarizeRange[1]))
        posterizeRange=int(posterizeRange)
        translatexRange=(int(translatexRange[0])/100, int(translatexRange[1])/100)
        translateyRange=(int(translateyRange[0])/100, int(translateyRange[1])/100)
        shearxRange=(int(shearxRange[0]), int(shearxRange[1]))
        shearyRange=(int(shearyRange[0]), int(shearyRange[1]))
        rotateRange=(int(rotateRange[0]), int(rotateRange[1]))
        randAugment=(int(randAugment[0]), int(randAugment[1]))

        ranges=[solarizeRange, posterizeRange, translatexRange, translateyRange, shearxRange, shearyRange, rotateRange, randAugment]
        if(premade):
            premade=True
        else:
            premade=False
        context = {'page':'Augment',
                    'augmentations': augmentations,
                    'premade': premade,
                    'ranges': ranges,
                    'numberOfImages': numberOfImages,
                    'augment': True}
        return render(request, 'photos/download.html', context)

    user = User.objects.get(username=request.user)
    try:
        dataset = user.dataset
    except Dataset.DoesNotExist:
        dataset = None

    if(not dataset):
        context['hasDataset']=False

    items = ["0","1","2","3","4","5","6","7","8","9"]
    context['list']=items
    return render(request, "photos/augment.html", context)



@login_required
def augmentDataset(request):
    if(request.method=="POST"):
        premade=request.POST.getlist('premade')[0]
        # clean up the string from ajax
        augmentations=unescape(request.POST.getlist('augmentations')[0])
        # evaluate the string as list
        augmentations=literal_eval(augmentations)

        ranges=request.POST.getlist('ranges')

        # evaluate the string as list
        ranges=literal_eval(ranges[0])
        print(ranges)

        numberOfImages=int(request.POST.get('numberOfImages'))
        print("num: ", numberOfImages)
        print("user: ", request.user)
        
        augmenters=[]
        if(premade=="True"):
            augmenters.append(iaa.RandAugment(ranges[7][0], ranges[7][1]))
            print("RandAugment")
        else:
            for augmentation in augmentations:
                match (augmentation):
                    case 'solarize':
                        augmenters.append(iaa.Solarize(1, threshold=ranges[0]))
                        print(augmentation)
                    case 'posterize':
                        augmenters.append(iaa.Posterize(ranges[1]))
                        print(augmentation)
                    case 'translatex':
                        augmenters.append(iaa.TranslateX(percent=ranges[2]))
                        print(augmentation)
                    case 'translatey':
                        augmenters.append(iaa.TranslateY(percent=ranges[3]))
                        print(augmentation)
                    case 'shearx':
                        augmenters.append(iaa.ShearX(ranges[4])) #degrees
                        print(augmentation)
                    case 'sheary':
                        augmenters.append(iaa.ShearY(ranges[5])) #degrees
                        print(augmentation)
                    case 'flipx':
                        augmenters.append(iaa.Fliplr(1))
                        print(augmentation)
                    case 'flipy':
                        augmenters.append(iaa.Flipud(1))
                        print(augmentation)
                    case 'rotate':
                        augmenters.append(iaa.Affine(rotate=ranges[6]))
                        print(augmentation)
                    case _:
                        print("illegal state")

        
        seq = iaa.Sequential(augmenters)
        dataset_folder = os.path.join(settings.MEDIA_ROOT, request.user.username, "dataset")
        augmented_folder = os.path.join(settings.MEDIA_ROOT, request.user.username, "augmented")
        try:
            shutil.rmtree(augmented_folder)
            shutil.copytree(dataset_folder, augmented_folder)

            for subdir, dirs, files in os.walk(augmented_folder):
                for file in files:
                    # Create the full file path
                    file_path = os.path.join(subdir, file)

                    # Check if the file is an image (optional)
                    if file.endswith('.jpg') or file.endswith('.png'):
                        # Open the image using PIL
                        image =np.array( Image.open(file_path))
                        
                        for i in range(numberOfImages):
                            # Apply the augmentations
                            
                            augmented_image = seq.augment_image(image)
                            augmented_image_pil = Image.fromarray(augmented_image)
                            # Save the augmented image in the same directory
                            augmented_file_path = os.path.join(subdir, f"augmented_{i}{file}")
                            augmented_image_pil.save(augmented_file_path, format='PNG')
        except Exception as e:
            print(f"An exception occurred: {e}")

            return JsonResponse({"message": "An error occured, likely because a previous augmentation process was still running. Please wait a minute and try starting a new augmentation."})
        return JsonResponse({'message': "Succesfully augmented the dataset, your download will begin shortly..."})
    return redirect("home")



def zip_folder_thread(queue, folder_path, output_path):
    zip_file = tempfile.NamedTemporaryFile(delete=False, dir=output_path)
    name=zip_file.name
    with ZipFile(zip_file, 'w') as zip_file:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                zip_file.write(file_path, os.path.relpath(file_path, folder_path))
    
    zip_file.close()
    queue.put(name)



@login_required
def zipDataset(request):
    if request.method == 'POST':
        queue = Queue()
        folder_path = os.path.normpath(os.path.join(settings.MEDIA_ROOT, request.user.username, "augmented"))
        output_path = os.path.normpath(os.path.join(settings.MEDIA_ROOT, request.user.username, "temp"))
        if folder_path:
            # delete the previous zip file
            shutil.rmtree(output_path)
            os.mkdir(output_path)

            # Start the zip process in a new thread
            thread = threading.Thread(target=zip_folder_thread, args=(queue, folder_path, output_path))
            thread.start()
            filename=queue.get()

            # Delete the augmented dataset since the zip file is created
            shutil.rmtree(folder_path)
            os.mkdir(folder_path)
            # Return a JSON response containing the URL to the temporary file
            return JsonResponse({'url': filename})
    return redirect("home")



@login_required
def download(request):
    filename = request.GET.get('filename')
    if filename:
        # Return a FileResponse containing the contents of the temporary file
        return FileResponse(open(filename, 'rb'), as_attachment=True, filename='dataset.zip')
    return redirect("home")
    



@login_required
def deleteDataset(request):
    if request.user.is_authenticated:
        user = User.objects.get(username=request.user)
        try:
            dataset = user.dataset  # 'dataset' is the related name defined in the OneToOneField
        except Dataset.DoesNotExist:
                dataset = None

        # Delete the dataset if it exists
        if dataset:
            dataset.delete()
        
        user_path = os.path.join(settings.MEDIA_ROOT, request.user.username)
        dataset_path = os.path.join(settings.MEDIA_ROOT, request.user.username, "dataset")
        augmented_path = os.path.join(settings.MEDIA_ROOT, request.user.username, "augmented")
        temp_path = os.path.join(settings.MEDIA_ROOT, request.user.username, "temp")
        
        try:
            if(os.path.exists(user_path)):
                shutil.rmtree(user_path)
        except Exception as e:
            print(e)
            return HttpResponse("Unable to delete dataset")

        try:
            os.makedirs(dataset_path)
            os.makedirs(augmented_path)
            os.makedirs(temp_path)
        except Exception as e:
            print(e)
            return HttpResponse("Unable to create user directories")

        return redirect("home")
