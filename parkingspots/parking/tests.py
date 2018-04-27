from django.test import TestCase
from django.test import Client
import json

# Run by calling ./manage.py test
from parking.models import ParkingSpot

class ParkingSpotTestCase(TestCase):
	def setUp(self):
		ParkingSpot.objects.create(name = 1, lat = 37.7811, lon = -122.3965, reserved = 0)# ridecell
		ParkingSpot.objects.create(name = 2, lat = 37.7841, lon = -122.4068, reserved = 0)# westfield
		ParkingSpot.objects.create(name = 3, lat = 37.7786, lon = -122.3893, reserved = 0)# att park
		ParkingSpot.objects.create(name = 4, lat = 37.7811, lon = -122.3927, reserved = 0)# dropbox

	def test_simple(self):# Create radius of 10 meters around ridecell. Ridecell should show up

		json_input = {	
			"lat" : 37.7811,
			"lon" : -122.3965,
			"radius" : 10
		}

		response = self.client.post('/parkingspots/available', json.dumps(json_input), content_type = "application/json")
		self.assertEqual(response.json(), [{'Latitude': 37.7811, 'Longitude': -122.3965, 'Parking ID': 1, 'Reserved': 0}])
	
	def test_reserve(self): # Create ridecell object, check reserved is 0, call get, check reserved is 1

		ridecell = ParkingSpot.objects.get(name = 1)
		self.assertEqual(ridecell.reserved, 0)
		self.client.get('/parkingspots/reserve/1/')

		ridecell = ParkingSpot.objects.get(name = 1)
		self.assertEqual(ridecell.reserved, 1)
	
	def test_radius_and_reserve(self): # Create radius of 200 at southpark (37.781296, -122.394273), ridecell and dropbox should show up

		json_input = {	
			"lat" : 37.781296,
			"lon" : -122.394273,
			"radius" : 200
		}

		response = self.client.post('/parkingspots/available', json.dumps(json_input), content_type = "application/json")
		self.assertEqual(response.json(), [{'Latitude': 37.7811, 'Longitude': -122.3965, 'Parking ID': 1, 'Reserved': 0}, 
			{'Latitude': 37.7811, 'Longitude': -122.3927, 'Parking ID': 4, 'Reserved': 0}])

		# Reserve dropbox location, call again, only ridecell should show up

		self.client.get('/parkingspots/reserve/4/')
		response = self.client.post('/parkingspots/available', json.dumps(json_input), content_type = "application/json")
		self.assertEqual(response.json(), [{'Latitude': 37.7811, 'Longitude': -122.3965, 'Parking ID': 1, 'Reserved': 0}])

	def test_all_functionality(self): # Search in 1 km radius around Ridecell, every location should show up now

		json_input = {	
			"lat" : 37.7811,
			"lon" : -122.3965,
			"radius" : 1000
		}

		response = self.client.post('/parkingspots/available', json.dumps(json_input), content_type = "application/json")
		self.assertEqual(response.json(), [{'Latitude': 37.7811, 'Longitude': -122.3965, 'Parking ID': 1, 'Reserved': 0}, 
			{'Latitude': 37.7841, 'Longitude': -122.4068, 'Parking ID': 2, 'Reserved': 0},
            {'Latitude': 37.7786, 'Longitude': -122.3893, 'Parking ID': 3, 'Reserved': 0},
            {'Latitude': 37.7811, 'Longitude': -122.3927, 'Parking ID': 4, 'Reserved': 0}])

		# Reserve every parking spot
		self.client.get('/parkingspots/reserve/4/')
		self.client.get('/parkingspots/reserve/2/')
		self.client.get('/parkingspots/reserve/3/')
		self.client.get('/parkingspots/reserve/1/')
		self.client.get('/parkingspots/reserve/1/')
		self.client.get('/parkingspots/reserve/4/')
		self.client.get('/parkingspots/reserve/1/')
		self.client.get('/parkingspots/reserve/1/') # test for idem potency 

		response = self.client.post('/parkingspots/available', json.dumps(json_input), content_type = "application/json")
		self.assertEqual(response.json(), []) # Should return empty now

		self.client.get('/') # GET home page, checks to see if freed all reserved spots
		response = self.client.post('/parkingspots/available', json.dumps(json_input), content_type = "application/json")
		self.assertEqual(response.json(), [{'Latitude': 37.7811, 'Longitude': -122.3965, 'Parking ID': 1, 'Reserved': 0}, 
			{'Latitude': 37.7841, 'Longitude': -122.4068, 'Parking ID': 2, 'Reserved': 0},
            {'Latitude': 37.7786, 'Longitude': -122.3893, 'Parking ID': 3, 'Reserved': 0},
            {'Latitude': 37.7811, 'Longitude': -122.3927, 'Parking ID': 4, 'Reserved': 0}])






# Ran 4 tests in 0.048s

