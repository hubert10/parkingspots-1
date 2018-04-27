from django.shortcuts import render
from django.http import JsonResponse
from .models import ParkingSpot
from django.conf.urls import url
from django.contrib import admin
from parking import views
import json
import geopy.distance


def home(request): # removes all reserved spots

    parking_spots = ParkingSpot.objects.all()
    pLocation = list()

    for p in parking_spots:
        p.reserved = 0
        p.save()
        pLocation.append((p.name, p.lat, p.lon, p.reserved))


    response_html = ''.join(str(pLocation))
    response_html += 'Released all reserved car spots'

    return JsonResponse(response_html, safe = False)


def reserve(request, pk):
    ps = ParkingSpot.objects.get(pk = pk)
    ps.reserved = 1
    ps.save()
    return render(request, 'reserve.html', {'ps':ps})

def available(request):
    if request.method == "POST":
        body_unicode = request.body.decode('utf-8')
        body = json.loads(body_unicode)



        ps = ParkingSpot.objects.all()
        pLocation = list()
        for p in ps: # used Geopy to get the distances between input coordinates and parking spots
            coord1 = (p.lat, p.lon)
            coord2 = (body['lat'], body['lon'])
            dist_between = geopy.distance.vincenty(coord1, coord2).m
            if body['radius'] >= dist_between and p.reserved == 0:
                pLocation.append({ 'Latitude' : p.lat , 'Longitude' : p.lon, 'Parking ID' : p.name, 'Reserved' : p.reserved })


        return JsonResponse(pLocation, safe = False)
    else:
        response_html = 'Send POST Request to this address!'

        return JsonResponse(response_html, safe = False)

