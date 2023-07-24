from django.db import models
from django.contrib.auth.models import User

class Dataset(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    creationDate = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.name