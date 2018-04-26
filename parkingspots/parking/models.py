# Create your models here.
from django.db import models
from django.contrib.auth.models import User


class ParkingSpot(models.Model):
    name = models.IntegerField("ID", unique=True)
    lat = models.IntegerField("Latitude")
    lon = models.IntegerField("Longitude")
