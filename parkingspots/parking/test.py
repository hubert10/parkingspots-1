def get_nearest_car(current_location, location_list):
    nearest_point = [{}, ]
    min_distance = 2000
    gmaps = googlemaps.Client(mlQKDHLKJQDhKLMJDKLQDhKJQD756565)
    current_driver = None
    car = None

    for i in location_list:
        origins = (current_location['lat'], current_location['lng'])
        res = i.get('current_location')

        jsoncurrent = res if type(res) is dict else json.loads(res)

        destinations = (jsoncurrent.get('lat'), jsoncurrent.get('lng'))
        matrix = gmaps.distance_matrix(origins, destinations)
        values = matrix['rows'][0]['elements'][0]

        tmp = int(values.get('distance').get('value'))

        if tmp < min_distance:
            min_distance = tmp
            nearest_point = [i['current_location'], ]
            car = i['id']
            current_driver = i['current_driver']
        pass

    return nearest_point, min_distance, car, current_driver


def get_location_distance(from_location, destination_location):
    gmaps = googlemaps.Client(key=settings.GOOGLEMAPS_KEY)
    origin = [from_location, ]
    destination = [destination_location, ]
    matrix = gmaps.distance_matrix(origin, destination)

    values = matrix['rows'][0]['elements'][0]
    tmp = int(values.get('distance').get('value'))
    distance = math.ceil(tmp / 1000)
    duration = values.get('duration').get('text')

    return distance, duration
