from django.shortcuts import render

# Create your views here.
from django.http import JsonResponse
from .models import ParkingSpot
from django.conf.urls import url
from django.contrib import admin
from parking import views
import json


def home(request):
    #if request.method == 'POST':
    parking_spots = ParkingSpot.objects.all()
    pLocation = list()



    for p in parking_spots:
        pLocation.append((p.name, p.lat, p.lon, p.reserved))

    #response_html = ' '.join(str(pName))
    #response_html += '<br>'
    response_html = ' '.join(str(pLocation))
    return JsonResponse(response_html)
    # else:
    #   #Edit the database for reserved
    #   return HttpResponse(response_html)

def reserve(request, pk):
    ps = ParkingSpot.objects.get(pk = pk)
    ps.reserved = 1
    ps.save()
    return render(request, 'reserve.html', {'ps':ps})

def available(request):
    if request.method == "POST":
        body_unicode = request.body.decode('utf-8')
        body = json.loads(body_unicode)
        print(body['radius'])


        ps = ParkingSpot.objects.all()
        pLocation = list()
        for p in ps:

            pLocation.append({ 'Parking ID' : p.name, 'Latitude' : p.lat, 'Longitude' : p.lon, 'Reserved' : p.reserved })


        return JsonResponse(pLocation, safe = False)

    #return render(request, 'reserve.html', {'ps':ps})
    
