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



class RideViewSet(viewsets.ModelViewSet):
    """
    This ressource is for Ride management
    please note that the ride may be followed or not by a booking

   """
    queryset = Ride.objects.all()
    serializer_class = RideSerializer
    http_method_names = ['get', 'post', 'put', 'delete']
    filter_backends = [filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = {'car': ['exact'], 'booking': ['exact'], 'customer': ['exact'],'driver': ['exact'], 'created': ['gte', 'lte', 'exact', 'gt', 'lt']}
    search_fields = ['^customer__first_name', '^customer__last_name', '^car__current_driver__first_name',
                     '^car__current_driver__id']
    ordering_fields = ['created', 'modified']

    if not firebase_admin._apps:
        cred = credentials.Certificate(
            settings.DRF_FIREBASE_AUTH['FIREBASE_SERVICE_ACCOUNT_KEY']
        )
        firebase = firebase_admin.initialize_app(cred)
    firebase_admin.get_app()

    def get_serializer_class(self):
        if self.action == 'list':
            return RideSerializer
        if self.action == 'retrieve':
            return RideSerializer

        return RideCreateSerializer

    def create(self, request, *args, **kwargs):

        ride_serialized = RideCreateSerializer(data=request.data)

        if ride_serialized.is_valid():
            service = get_object_or_404(Service, pk=ride_serialized.validated_data['service'])
            vehicle_type = get_object_or_404(VehicleType, pk=ride_serialized.validated_data['vehicle_type'])

            if service.has_package is True:
                package = get_object_or_404(Service, pk=ride_serialized.validated_data['package'])
                pricing_card = PricingCard.objects.get(pricing_package=package, pricing_vehicle_type=vehicle_type)
            else:
                try:
                    pricing_card = PricingCard.objects.get(
                        pricing_service=service,
                        pricing_vehicle_type=vehicle_type)
                except ObjectDoesNotExist:
                    return Response(_('No pricing found for this service'), status=status.HTTP_404_NOT_FOUND)

            pricing = pricing_card

            # get_object_or_404(PricingCard.objects.filter().values(), pk=pricing_card[0])

            if 'pickup_location' not in request.data:
                pickup_location = None
            else:
                pickup_location = Location(
                    address=ride_serialized.validated_data['pickup_location']['address'],
                    lat=ride_serialized.validated_data['pickup_location']['lat'],
                    lng=ride_serialized.validated_data['pickup_location']['lng']
                )
            if 'dropoff_location' not in request.data:
                dropoff_location = None
            else:
                dropoff_location = Location(
                    address=ride_serialized.validated_data['dropoff_location']['address'],
                    lat=ride_serialized.validated_data['dropoff_location']['lat'],
                    lng=ride_serialized.validated_data['dropoff_location']['lng']
                )


            # this area is for driver search
            from_location = {'lat': 14.7195635, 'lng': -17.45886619999999}

            to_location = {'lat': 14.7195635, 'lng': -17.45886619999999}

            if 'pickup_location' in ride_serialized.validated_data:
                from_location = {'lat': ride_serialized.validated_data['pickup_location']['lat'], 'lng': ride_serialized.validated_data['pickup_location']['lng']}

            if 'dropoff_location' in ride_serialized.validated_data:
                to_location = {'lat': ride_serialized.validated_data['dropoff_location']['lat'], 'lng': ride_serialized.validated_data['dropoff_location']['lng']}

            search_car = Vehicles.objects.filter(status='ONLINE').all()

            car_list = []

            for car in search_car:

                car_list.append(
                    {'id': car.id, 'current_location': car.current_location,
                     'current_driver': car.current_driver})

            if service.service_type == 'IN_AREA':
                location, distance, car, current_driver = get_nearest_car(from_location, car_list)
            else:
                location = None
                distance = 0
                current_driver = None
                car = None
            # this area is for ride fee processing

            if pricing.pricing_basic_unit == 'DURATION':
                distance = 0
                duration = 0
            else:
                distance, duration = get_location_distance(from_location, to_location)

            booking_data = None if 'booking' not in ride_serialized.validated_data else ride_serialized.validated_data.pop(
                'booking')
            if pickup_location is not None:
                pickup_location.save()
            if dropoff_location is not None:
                dropoff_location.save()

            booking = None if booking_data is None else Booking(booking_date=booking_data['booking_date'])

            if booking is not None:
                booking.save()

            ride = Ride(
                distance=distance,
                duration=duration,
                driver=None if car is None else Vehicles.objects.filter(id=car).get().current_driver,
                booking=None if booking_data is None else booking,
                pickup_location=pickup_location,
                dropoff_location=dropoff_location,
                is_ride_ended=False,
                car=None if car is None else get_object_or_404(Vehicles, id=car),
                customer=get_object_or_404(User, pk=ride_serialized.validated_data['customer']),
                vehicle_type=get_object_or_404(VehicleType, pk=ride_serialized.validated_data['vehicle_type']),
                service=service,
                package=None if 'package' not in ride_serialized.validated_data else ride_serialized.validated_data[
                    'package'],
            )

            if pricing.pricing_basic_unit == 'MILES_KM':
                dist_to_bill = distance - pricing.distance_in_charge
                fee = pricing.base_fare + (pricing.distance_charge * dist_to_bill)

            elif pricing.pricing_basic_unit == 'FIXED':
                fee = pricing.base_fare
            else:
                fee = 0

            promo = None
            if 'promo_code' in ride_serialized.validated_data and len(
                    str(ride_serialized.validated_data['promo_code'])):
                try:
                    promo = Promotion.objects.get(code=str(ride_serialized.validated_data['promo_code']),
                                                  start_date__gte=datetime.date(), end_date__lte=datetime.date(),
                                                  is_active=True)
                except ObjectDoesNotExist:
                    pass

            if car is None:
                pass
            else:

                d = User.objects.filter(pk=Vehicles.objects.filter(id=car).get().current_driver.id).get()
                u = User.objects.filter(pk=ride_serialized.validated_data['customer']).get()

                print(d)
                rc = list()

                rd = list()
                for t in u.device.all():
                    if t.token is not None:
                        rc.append(t.token)

                for t in d.device.all():
                    if t.token is not None:
                        rd.append(t.token)

            if car is not None:
                notif = messaging.Notification(title=str(_('New Ride')),
                                               body='' if ride.pickup_location is None else _(
                                                   'Pickup location') + ' ' + ride.pickup_location.address)

                notif2 = messaging.Notification(title=str(_('New Ride')),
                                                body='' if ride.pickup_location is None else _(
                                                    'Pickup location') + ' ' + ride.pickup_location.address)

                androidnotification = messaging.AndroidNotification(title=str(_('New Ride')),
                                                                    body=service.name if ride.pickup_location is None else service.name+' '+str(_('Pickup location')) + ' ' + ride.pickup_location.address,
                                                                    default_vibrate_timings=True, default_sound=True,
                                                                    priority='high')
                androidnotification2 = messaging.AndroidNotification(title=str(_('New Ride')),
                                                                     body=str(_(
                                                                         'Your ride has been assigned, to driver ')) + d.first_name + ' ' + d.last_name + str(_('car number')) + Vehicles.objects.filter(id=car).get().number_plate,
                                                                     default_vibrate_timings=True,
                                                                     default_sound=True,
                                                                     priority='high')
                message = messaging.MulticastMessage(rd, notification=notif,
                                                     data={'ride_id': str(ride.id), 'type': 'new_ride'},
                                                     android=messaging.AndroidConfig(notification=androidnotification))
                message2 = messaging.MulticastMessage(rc, notification=notif2,
                                                      data={'ride_id': str(ride.id), 'type': 'driver_assigned'},
                                                      android=messaging.AndroidConfig(
                                                          notification=androidnotification2))
                messaging.send_multicast(message)
                messaging.send_multicast(message2)
            ride.save()
            extra_amount = 0

            if promo is not None:
                if promo.type == 'FLAT_RATE':
                    extra_amount = extra_amount - promo.value
                else:
                    extra_amount = extra_amount - (fee * (promo.value / 100))

            bill = Bills(
                payment=None if 'payment' not in ride_serialized.validated_data else get_object_or_404(PaymentMethod,
                                                                                                       pk=
                                                                                                       ride_serialized.validated_data[
                                                                                                           'payment']),
                ride=ride,
                extra_amount=extra_amount,
                promotion=None if promo is None else promo.id,
                total_amount=fee - extra_amount,
                ride_amount=fee
            )

            bill.save()

            return Response(BillsSerializer(bill).data, status=status.HTTP_201_CREATED)

        else:
            return Response(ride_serialized.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['put'], serializer_class=RideUpdateCarSerializer)
    def setcar(self, request, *args, **kwargs):
        instance = self.get_object()

        carserializer = RideUpdateCarSerializer(data=request.data)

        if carserializer.is_valid():
            car = get_object_or_404(Vehicles, id=carserializer.validated_data['car'])
            Ride.objects.filter(pk=instance).update(car=car.id, driver=car.current_driver)

            d = car.current_driver
            u = User.objects.filter(id=instance.id).get()
            rc = list()
            rd = list()

            for t in u.device.all():
                if t.token is not None:
                    rc.append(t.token)

            for t in d.device.all():
                if t.token is not None:
                    rd.append(t.token)

            notif = messaging.Notification(title=str(_('New Ride')),
                                           body='' if instance.pickup_location is None else _(
                                               'Pickup location') + ' ' + instance.pickup_location.address)

            notif2 = messaging.Notification(title=str(_('New Driver')),
                                            body=str(_('Your ride has been assigned, to driver ')) + d.first_name + ' ' + d.last_name + str(_('car number')) + car.number_plate)

            androidnotification = messaging.AndroidNotification(title=str(_('New Ride')),
                                                                body=instance.service.name if instance.pickup_location is None else instance.name + ' ' + str(
                                                                    _('Pickup location')) + ' ' + instance.pickup_location.address,
                                                                default_vibrate_timings=True, default_sound=True,
                                                                priority='high')
            androidnotification2 = messaging.AndroidNotification(title=str(_('New Driver')),
                                                                 body=str(_(
                                                                     'Your ride has been assigned, to driver ')) + d.first_name + ' ' + d.last_name + str(
                                                                     _('car number')) + car.number_plate,
                                                                 default_vibrate_timings=True,
                                                                 default_sound=True,
                                                                 priority='high')
            message = messaging.MulticastMessage(rd, notification=notif,
                                                 data={'ride_id': str(instance.id), 'type': 'new_ride'},
                                                 android=messaging.AndroidConfig(notification=androidnotification))
            message2 = messaging.MulticastMessage(rc, notification=notif2,
                                                  data={'ride_id': str(instance.id), 'type': 'driver_assigned'},
                                                  android=messaging.AndroidConfig(
                                                      notification=androidnotification2))
            messaging.send_multicast(message)
            messaging.send_multicast(message2)

        else:
            return Response(carserializer.errors)


    @action(detail=True, methods=['get'], serializer_class=BillsSerializer)
    def get_bill(self, request, *args, **kwargs):
        instance = self.get_object()
        bill = get_object_or_404(Bills, ride=instance)
        serializer = BillsSerializer(bill)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], serializer_class=RideSerializer)
    def estimate(self, request, *args, **kwargs):

        ride_serialized = RideCreateSerializer(data=request.data)

        if ride_serialized.is_valid():
            service = get_object_or_404(Service, pk=ride_serialized.validated_data['service'])
            vehicle_type = get_object_or_404(VehicleType, pk=ride_serialized.validated_data['vehicle_type'])

            if service.has_package is True:
                package = get_object_or_404(Service, pk=ride_serialized.validated_data['package'])
                pricing_card = PricingCard.objects.get(pricing_package=package, pricing_vehicle_type=vehicle_type)
            else:
                try:
                    pricing_card = PricingCard.objects.get(
                        pricing_service=service,
                        pricing_vehicle_type=vehicle_type)
                except ObjectDoesNotExist:
                    return Response(_('No pricing found for this service'), status=status.HTTP_404_NOT_FOUND)

            pricing = pricing_card

            # get_object_or_404(PricingCard.objects.filter().values(), pk=pricing_card[0])

            pickup_location = Location(
                address=ride_serialized.validated_data['pickup_location']['address'],
                lat=ride_serialized.validated_data['pickup_location']['lat'],
                lng=ride_serialized.validated_data['pickup_location']['lng']
            ) if 'pickup_location' in ride_serialized.validated_data else None,

            dropoff_location = Location(
                address=ride_serialized.validated_data['dropoff_location']['address'],
                lat=ride_serialized.validated_data['dropoff_location']['lat'],
                lng=ride_serialized.validated_data['dropoff_location']['lng']
            ) if 'dropoff_location' in ride_serialized.validated_data else None,


            # this area is for driver search
            from_location = {'lat': 14.7195635, 'lng': -17.45886619999999}

            to_location = {'lat': 14.7195635, 'lng': -17.45886619999999}

            if 'pickup_location' in ride_serialized.validated_data:
                from_location = {'lat': ride_serialized.validated_data['pickup_location']['lat'],
                                 'lng': ride_serialized.validated_data['pickup_location']['lng']}

            if 'dropoff_location' in ride_serialized.validated_data:
                to_location = {'lat': ride_serialized.validated_data['dropoff_location']['lat'],
                               'lng': ride_serialized.validated_data['dropoff_location']['lng']}

            search_car = Vehicles.objects.filter(status='ONLINE').all()

            car_list = []

            for car in search_car:
                car_list.append(
                    {'id': car.id, 'current_location': car.current_location,
                     'current_driver': car.current_driver})

            if service.service_type == 'IN_AREA':
                location, distance, car, current_driver = get_nearest_car(from_location, car_list)
            else:
                location = None
                distance = 0
                current_driver = None
                car = None

            # this area is for ride fee processing

            if pricing.pricing_basic_unit == 'DURATION':
                distance = 0
                duration = 0
            else:
                distance, duration = get_location_distance(from_location, to_location)

            booking_data = None if 'booking' not in ride_serialized.validated_data else ride_serialized.validated_data.pop(
                'booking')

            booking = None if booking_data is None else Booking(booking_date=booking_data['booking_date'])

            ride = Ride(
                distance=distance,
                duration=duration,
                booking=None if booking_data is None else booking,
                #pickup_location_id=pickup_location,
                #dropoff_location_id=dropoff_location,
                is_ride_ended=False,
                car=None if car is None else get_object_or_404(Vehicles, id=car),
                customer=get_object_or_404(User, pk=ride_serialized.validated_data['customer']),
                vehicle_type=get_object_or_404(VehicleType, pk=ride_serialized.validated_data['vehicle_type']),
                service=service,
                package=None if 'package' not in ride_serialized.validated_data else ride_serialized.validated_data[
                    'package'],
            )

            if pricing.pricing_basic_unit == 'MILES_KM':
                dist_to_bill = distance - pricing.distance_in_charge
                fee = pricing.base_fare + (pricing.distance_charge * dist_to_bill)

            elif pricing.pricing_basic_unit == 'FIXED':
                fee = pricing.base_fare
            else:
                fee = 0

            promo = None
            if pricing.pricing_basic_unit == 'MILES_KM':
                if 'promo_code' in ride_serialized.validated_data and len(str(ride_serialized.validated_data['promo_code'])):
                    try:
                        promo = Promotion.objects.get(code=str(ride_serialized.validated_data['promo_code']),
                                                      start_date__gte=datetime.date(), end_date__lte=datetime.date(),
                                                      is_active=True)
                    except ObjectDoesNotExist:
                        pass

            # ride.save()
            extra_amount = 0

            if promo is not None:
                if promo.type == 'FLAT_RATE':
                    extra_amount = extra_amount - promo.value
                else:
                    extra_amount = extra_amount - (fee * (promo.value / 100))

            bill = Bills(
                payment=None if 'payment' not in ride_serialized.validated_data else get_object_or_404(PaymentMethod,
                                                                                                       pk=
                                                                                                       ride_serialized.validated_data[
                                                                                                           'payment']),
                ride=ride,
                extra_amount=extra_amount,
                promotion=None if promo is None else promo.id,
                total_amount=fee - extra_amount,
                ride_amount=fee
            )

            return Response(BillsSerializer(bill).data, status=status.HTTP_201_CREATED)

        else:
            return Response(ride_serialized.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['put'], serializer_class=RideSerializer)
    def start(self, request, *args, **kwargs):
        instance = self.get_object()
        car = Vehicles.objects.filter(pk=instance.car.id).update(status='BUSY')
        ride = Ride.objects.filter(pk=instance.id).update(is_ride_started=True, start_date=datetime.now())

        u = User.objects.filter(pk=instance.customer.id).get()
        d = User.objects.filter(pk=instance.driver.id).get()

        rc = list()
        rd = list()

        for t in u.device.all():
            if t.token is not None:
                rc.append(t.token)

        for t in d.device.all():
            if t.token is not None:
                rd.append(t.token)

        notif = messaging.Notification(title=str(_('Ride starting')), body='' if instance.pickup_location is None else str(_('Pickup location')) + ' ' + instance.pickup_location.address)
        androidnotification = messaging.AndroidNotification(title=str(_('Ride starting')), body='' if instance.pickup_location is None else str(_('Pickup location')) + ' ' + instance.pickup_location.address,
                                                            default_vibrate_timings=True, default_sound=True,
                                                            priority='high')
        message = messaging.MulticastMessage(rc, notification=notif, data={'ride_id': str(instance.id), 'type': 'start_ride'}, android=messaging.AndroidConfig(notification=androidnotification))
        messaging.send_multicast(message)

        return Response(status=status.HTTP_200_OK)

    @action(detail=True, methods=['put'], serializer_class=RideSerializer)
    def end(self, request, *args, **kwargs):
        instance = self.get_object()

        rideObject = Ride.objects.filter(pk=instance.id)
        rideObject.update(is_ride_ended=True, end_date=datetime.now())
        ride = rideObject.get()

        u = User.objects.filter(pk=instance.customer.id).get()
        d = User.objects.filter(pk=instance.driver.id).get()
        s = User.objects.filter(is_staff=True).all()

        rc = list()

        if len(s) > 0:
            for staff in s:
                for st in staff.device.all():
                    if st.token is not None:
                        rc.append(st.token)

        for t in u.device.all():
            if t.token is not None:
                rc.append(t.token)
        for t in d.device.all():
            if t.token is not None:
                rc.append(t.token)

        notif = messaging.Notification(title=str(_('Ride Ended') if ride.is_ride_started is None else _('Ride Canceled')), body='' if instance.pickup_location is None else _(
            'Pickup location') + ' ' + instance.dropoff_location.address)
        androidnotification = messaging.AndroidNotification(title=str(_('Ride Ended') if ride.is_ride_started is None else _('Ride Canceled')),
                                                            body='' if instance.pickup_location is None else _(
                                                                'Pickup location') + ' ' + instance.dropoff_location.address,
                                                            default_vibrate_timings=True, default_sound=True,
                                                            priority='high')
        message = messaging.MulticastMessage(rc, notification=notif, data={'ride_id': str(ride.id), 'type': 'end_ride'},
                                             android=messaging.AndroidConfig(notification=androidnotification))

        if ride.is_ride_started is True:
            Vehicles.objects.filter(pk=instance.car.id).update(status='ONLINE')

        billObj = Bills.objects.filter(ride__id=ride.id)

        bill = billObj.get()
        rideObject.update(is_ride_ended=True, end_date=datetime.now())
        ride = rideObject.get()
        duration = ((ride.end_date - ride.start_date).total_seconds()/60)/60
        duration = math.ceil(duration)
        service = Service.objects.filter(pk=ride.service.id).get()

        if service.has_package is True:
            package = get_object_or_404(Service, pk=ride.package)
            pricing_card = PricingCard.objects.get(pricing_package=package, pricing_vehicle_type__id=ride.vehicle_type.id)
        else:
            try:
                pricing_card = PricingCard.objects.get(
                    pricing_service=service,
                    pricing_vehicle_type__id=ride.vehicle_type.id)
            except ObjectDoesNotExist:
                return Response(_('No pricing found for this service'), status=status.HTTP_404_NOT_FOUND)

        pricing = pricing_card

        if pricing.pricing_basic_unit == 'DURATION':
            rest_duartion = 0 if duration <= pricing.max_duration_in_charge else duration - pricing.max_duration_in_charge

            price_in_charge = duration * pricing.base_fare
            rest_duartion_price = rest_duartion * pricing.duration_charge
            fee = price_in_charge + rest_duartion_price
            promo = None if bill.promotion is None else Promotion.objects.filter(id=bill.promotion)
            extra_amount = 0
            if promo is not None:
                extra_amount = extra_amount - (fee * (promo.value / 100))

            Bills.objects.filter(ride__id=ride.id).update(extra_amount=extra_amount, total_amount=fee - extra_amount, ride_amount=fee)

        messaging.send_multicast(message)

        return Response(status=status.HTTP_200_OK)

    @action(detail=True, methods=['put'], serializer_class=RideSerializer)
    def setcar(self, request, *args, **kwargs):
        instance = self.get_object()
        newcar = None if 'car' not in request.data else request.data['car']

        try:
            car = Vehicles.objects.filter(pk=newcar)
        except ObjectDoesNotExist:
            return Response({'details': _('Car with the provided information do not exist')}, status=status.HTTP_404_NOT_FOUND)

        car_info = car.get()
        car.update(status='BUSY')
        ride = Ride.objects.filter(pk=instance.id).update(car=car_info.id, driver=car_info.current_driver.id)

        u = User.objects.filter(pk=instance.customer.id).get()
        d = User.objects.filter(pk=instance.driver.id).get()
        rc = list()
        rd = list()

        for t in u.device.all():
            if t.token is not None:
                rc.append(t.token)

        for t in d.device.all():
            if t.token is not None:
                rd.append(t.token)

        notif = messaging.Notification(title=str(_('New Ride')),
                                       body='' if instance.pickup_location is None else _(
                                           'Pickup location') + ' ' + instance.pickup_location.address)

        notif2 = messaging.Notification(title=str(_('New Ride')),
                                        body=str(_('Your ride has been assigned, to driver ')) + d.first_name + ' ' + d.last_name + str(_('car number')) + car.get().number_plate)

        androidnotification = messaging.AndroidNotification(title=_('New Ride'),
                                                            body=instance.service.name if instance.pickup_location is None else instance.service.name + ' ' + str(
                                                                _(
                                                                    'Pickup location')) + ' ' + instance.pickup_location.address,
                                                            default_vibrate_timings=True, default_sound=True,
                                                            priority='high')
        androidnotification2 = messaging.AndroidNotification(title=_('New Ride'),
                                                             body=str(_(
                                                                 'Your ride has been assigned, to driver ')) + d.first_name + ' ' + d.last_name + str(
                                                                 _('car number')) + car.get().number_plate,
                                                             default_vibrate_timings=True,
                                                             default_sound=True,
                                                             priority='high')
        message = messaging.MulticastMessage(rd, notification=notif,
                                             data={'ride_id': instance.id, 'type': 'new_ride'},
                                             android=messaging.AndroidConfig(notification=androidnotification))
        message2 = messaging.MulticastMessage(rc, notification=notif2,
                                              data={'ride_id': instance.id, 'type': 'driver_assigned'},
                                              android=messaging.AndroidConfig(
                                                  notification=androidnotification2))
        messaging.send_multicast(message)
        messaging.send_multicast(message2)

        return Response(status=status.HTTP_200_OK)
