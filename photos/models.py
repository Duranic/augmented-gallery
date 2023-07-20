from django.db import models
from django.contrib.auth.models import User

class Dataset(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    creationDate = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.name

class Category(models.Model):
    name= models.CharField(max_length=100,null=False,blank=False)
    def __str__(self):
        return self.name

class Photo(models.Model):
    category=models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    image= models.ImageField(null=False, blank=False)
    description= models.CharField(max_length=100,null=False,blank=False)
    def __str__(self):
        return self.description