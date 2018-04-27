# Create your models here.
from django.db import models
from django.contrib.auth.models import User


class ParkingSpot(models.Model):
    name = models.IntegerField("ID", unique=True)
    lat = models.FloatField("Latitude")
    lon = models.FloatField("Longitude")
    reserved = models.IntegerField("Reserved", default = 0)

    def __int__(self):
    	return self.name


# {	
# 	"lat" : 37.7811,
# 	"lon" : -122.3965,
# 	"radius" : 1000
# } Testing with this .json file structure in postman
