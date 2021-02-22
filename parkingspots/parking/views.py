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


    
    
    
    
    
    class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    http_method_names = ['get', 'post', 'put', 'delete']
    filter_backends = [filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['profile_type', 'email', 'phone_number', 'last_name', 'first_name']
    search_fields = ['=profile_type', '=email', 'phone_number', '^last_name', '^first_name']
    ordering_fields = ['created', 'modified']

    def create(self, request, *args, **kwargs):

        serializer = UserSerializer(data=request.data)

        if serializer.is_valid():
            groups_data = serializer.validated_data.pop('groups')

            user = User(
                username=serializer.validated_data['email'],
                first_name=None if 'first_name' not in serializer.validated_data else serializer.validated_data[
                    'first_name'],
                last_name=None if 'last_name' not in serializer.validated_data else serializer.validated_data[
                    'last_name'],
                email=serializer.validated_data['email'],
                avatar=None if 'avatar' not in serializer.validated_data else serializer.validated_data['avatar'],
                account_type='NORMAL' if 'account_type' not in serializer.validated_data else serializer.validated_data[
                    'account_type'],
                phone_number='' if 'phone_number' not in serializer.validated_data else serializer.validated_data[
                    'phone_number'],
                profile_type='CUSTOMER' if 'profile_type' not in serializer.validated_data else
                serializer.validated_data['profile_type'],
                is_staff=True if 'profile_type' in serializer.validated_data and serializer.validated_data[
                    'profile_type'] == 'STAFF' else False
            )

            if 'password' in serializer.validated_data:
                user.set_password(serializer.validated_data['password'])

                if not is_password_valid(serializer.validated_data['password']):
                    return Response({"details": _(
                        "The password must contain at least 1 uppercase letter, 1 special character and a minimum length of 8 characters")},
                                    status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"details": _("Please provide a password")}, status=status.HTTP_400_BAD_REQUEST)

            user.save()

            if user.account_type != 'NORMAL':
                Wallet(
                    user=user.id
                ).save()

            for group_data in groups_data:
                user.groups.add(group_data)
            user.save()

            if 'account_type' in serializer.validated_data and serializer.validated_data['account_type'] == 'WALLET':
                Wallet(user=user).save()

            user_serialized = UserSerializer(user).data

            return Response(user_serialized, status=status.HTTP_201_CREATED)
        else:

            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):

        instance = self.get_object()
        user = User.objects.filter(pk=instance.id).get()
        if user.account_type != 'NORMAL':
            if 'account_type' in request.data and request.data['account_type'] == 'NORMAL':
                return Response(status=status.HTTP_400_BAD_REQUEST)

        if 'profile_type' in request.data:
            instance.is_staff = True if request.data['profile_type'] == 'STAFF' else False

        if 'password' in request.data:
            if len(request.data['password']) < 1 or request.data['password'] == 'undefined':
                pass
            else:

                if not is_password_valid(request.data['password']):
                    return Response({"details": _(
                        "The password must contain at least 1 uppercase letter, 1 special character and a minimum length of 8 characters")},

                                    status=status.HTTP_400_BAD_REQUEST)
                instance.set_password(request.data['password'])

                instance.save()

        data = request.data.copy()
        data.pop('password')
        partial = kwargs.pop('partial', True)
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)

        self.perform_update(serializer)

        return Response(serializer.data, status=status.HTTP_200_OK)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()

        serializer = UserReadSerializer(instance)
        return Response(serializer.data)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = UserReadSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = UserReadSerializer(queryset, many=True)
        return Response(serializer.data)

    def perform_update(self, serializer):
        serializer.save()

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    @action(detail=True, methods=['put'], serializer_class=PasswordSerializer)
    def change_password(self, request, *args, **kwargs):
        """
         Change user password by providing old_password and new_password. The minimun length is 8
         In addition, the password must have at least one uppercase letter, one number and one special character
        """
        user = self.get_object()
        serializer = PasswordSerializer(data=request.data)
        user_serializer = UserSerializer(user)
        if serializer.is_valid():
            if not user.check_password(serializer.data.get('old_password')):
                return Response({"old_password": ["WRONG_PASSWORD"]}, status=status.HTTP_400_BAD_REQUEST)

            if is_password_valid(serializer.data.get('new_password')):
                user.set_password(serializer.data.get('new_password'))
                user.save()
                return Response(status=status.HTTP_200_OK)
            else:
                return Response({"details": _(
                    "The password must contain at least 1 uppercase letter, 1 special character and a minimum length of 8 characters")},
                                status=status.HTTP_400_BAD_REQUEST)

        else:
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['GET'], detail=False, url_path='me', url_name='me')
    def me(self, request, *args, **kwargs):

        try:
            User.objects.get(
                Q(email=get_current_authenticated_user()) | Q(phone_number=get_current_authenticated_user())
            )

            current_user = get_object_or_404(User, email=get_current_authenticated_user())

            user_serialized = UserSerializer(current_user).data

            return Response(user_serialized)
        except User.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

    @action(methods=['POST'], detail=False, serializer_class=PasswordResetRequestSerializer)
    def requestpasswordreset(self, request, *args, **kwargs):

        password_resetRequest_serializer = PasswordResetRequestSerializer(data=request.data)

        if password_resetRequest_serializer.is_valid():

            try:
                user = User.objects.filter(email=password_resetRequest_serializer.validated_data['email']).get()
                print(user.email + " ##")

                tmp = UserTmpPassWord.objects.filter(email=user.email)

                code = id_generator()
                if tmp.exists():
                    UserTmpPassWord.objects.filter(email=user.email).update(code=code)
                else:
                    UserTmpPassWord(
                        email=user.email,
                        code=code
                    ).save()

                message = '<html><body>' + str(
                    _('<p>Hi,<br/><br/> You asked a password reset, please use the code below to reset your password.')) +str(
                    '<br/><br/><b>') + code + str(
                    '</b></p><p style="color:#DB7D34">Izycab Team</p></body></html>')

                from smtplib import SMTPAuthenticationError
                try:
                    send_mail(subject=_('Izycab password reset'), message=message,
                              from_email="IZYCAB<" + settings.DEFAULT_FROM_EMAIL + ">",
                              recipient_list=[user.email],
                              html_message=message, fail_silently=False)
                    return Response()
                except:
                    return Response(status=status.HTTP_501_NOT_IMPLEMENTED)

            except User.DoesNotExist:
                return Response(status=status.HTTP_404_NOT_FOUND)

        else:
            return Response(password_resetRequest_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['POST'], detail=False, serializer_class=AccountPassworsResetSerializer)
    def passwordreset(self, request, *args, **kwargs):

        password_request_serializer = AccountPassworsResetSerializer(data=request.data)

        if password_request_serializer.is_valid():

            try:
                tmp = UserTmpPassWord.objects.filter(code=password_request_serializer.validated_data['code']).get()
                password = password_request_serializer.validated_data['password']
                if is_password_valid(password):
                    user = User.objects.filter(email=tmp.email).get()
                    user.set_password(password)
                    user.save()
                    tmp.delete()
                    return Response(status=status.HTTP_200_OK)
                else:
                    return Response({"details": _(
                        "The password must contain at least 1 uppercase letter, 1 special character and a minimum length of 8 characters")},
                        status=status.HTTP_400_BAD_REQUEST)

            except UserTmpPassWord.DoesNotExist:

                return Response(status=status.HTTP_404_NOT_FOUND)

        else:
            return Response(password_request_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['GET'], detail=True, url_path='enable', url_name='enable', serializer_class=UserSerializer)
    def enable(self, request, *args, **kwargs):
        instance = self.get_object()
        User.objects.filter(pk=instance.id).update(is_active=True)
        serializer = self.get_serializer(User.objects.filter(pk=instance.id))
        return Response()

    @action(methods=['GET'], detail=True, url_path='disable', url_name='disable', serializer_class=UserSerializer)
    def disable(self, request, *args, **kwargs):
        instance = self.get_object()
        User.objects.filter(pk=instance.id).update(is_active=False)
        serializer = self.get_serializer(User.objects.filter(pk=instance.id))
        return Response()

    @action(methods=['POST'], detail=True, serializer_class=DeviceTokenSerializer)
    def addtoken(self, request, *args, **kwargs):
        instance = self.get_object()
        serializers = DeviceTokenSerializer(data=request.data)

        if serializers.is_valid():
            device = DeviceToken(
                token=serializers.validated_data['token']
            )

            device.save()

            UserDeviceToken(
                token_id=device.id,
                user_id=instance.id
            ).save()

            serialize = UserReadSerializer(instance)
            return Response()

        else:
            return Response(serializers.errors, status=status.HTTP_400_BAD_REQUEST)
