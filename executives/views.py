from .serializers import *
from users.serializers import *
from rest_framework import generics,permissions
from .models import *
from users.models import *
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import NotFound
from django.shortcuts import get_object_or_404
from django.contrib.auth import logout
from .utils import send_otp, generate_otp
from rest_framework.permissions import AllowAny
from django.db import transaction
from django.db.models import Avg
from payments.models import CoinConversion
from analytics.models import CoinRedemptionRequest
from payments.serializers import CoinRedemptionRequestSerializer
from executives.permissions import IsManagerExecutive
from rest_framework.permissions import IsAuthenticated
from django.http import Http404
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.contrib.auth.hashers import make_password
from django.contrib.sessions.models import Session
from django.contrib.auth.hashers import make_password, check_password
from django.db.models.functions import Cast, Substr
from django.db.models import IntegerField

#OTPAUTH
class ExeRegisterOrLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        mobile_number = request.data.get("mobile_number")
        password = request.data.get("password")

        if not mobile_number or not password:
            return Response({
                "message": "Mobile number and password are required.",
                "status": False
            }, status=status.HTTP_400_BAD_REQUEST)

        device_id = request.data.get("device_id") or str(uuid.uuid4())

        if BlockedDevices.objects.filter(device_id=device_id, is_banned=True).exists():
            return Response({
                "message": "Your device is banned.",
                "status": False
            }, status=status.HTTP_403_FORBIDDEN)

        otp = generate_otp()

        try:
            executive = Executives.objects.get(mobile_number=mobile_number)

            if executive.online and not executive.is_logged_out and executive.device_id != device_id:
                return Response(
                    {"message": "Already logged in on another device. Please logout from that device to continue."},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            if executive.online and executive.check_activity_timeout():
                executive.online = False
                executive.is_logged_out = True
                executive.save(update_fields=['online', 'is_logged_out'])
                return Response(
                    {"message": "Session expired. Please login again."},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            if not check_password(password, executive.password):
                return Response({
                    "message": "Invalid password.",
                    "status": False
                }, status=status.HTTP_401_UNAUTHORIZED)

            executive.device_id = device_id
            executive.online = False  
            executive.is_logged_out = True
            executive.save()

            if send_otp(mobile_number, otp):
                executive.otp = otp
                executive.save()
                return Response({
                    "message": "OTP sent to your mobile number.",
                    "id": executive.id,
                    "executive_id": executive.executive_id,
                    "name": executive.name,
                    "device_id": device_id,
                    "status": True,
                    "otp": otp,
                    "is_suspended": executive.is_suspended,
                    "is_banned": executive.is_banned,
                    "online": executive.online,
                    "auto_logout_minutes": executive.AUTO_LOGOUT_MINUTES if hasattr(executive, 'AUTO_LOGOUT_MINUTES') else None
                }, status=status.HTTP_200_OK)

            return Response({
                "message": "Failed to send OTP.",
                "status": False
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Executives.DoesNotExist:
            return Response({
                "message": "Executive not found. Please register first.",
                "status": False
            }, status=status.HTTP_404_NOT_FOUND)

            
class ExeVerifyOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        mobile_number = request.data.get("mobile_number")
        otp = request.data.get("otp")
        device_id = request.data.get("device_id")  

        try:
            executive = Executives.objects.get(mobile_number=mobile_number, otp=otp)
            
            if executive.online and not executive.is_logged_out and executive.device_id != device_id:
                return Response(
                    {"message": "Already logged in on another device. Please logout from that device to continue."},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            if executive.online and executive.check_activity_timeout():
                executive.online = False
                executive.is_logged_out = True
                executive.save(update_fields=['online', 'is_logged_out'])
                return Response(
                    {"message": "Session expired. Please login again."},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            executive.is_verified = True
            executive.otp = None 
            executive.online = True
            executive.is_logged_out = False
            executive.last_activity = timezone.now()
            executive.device_id = device_id
            executive.save()

            return Response({
                "message": "OTP verified successfully.",
                "id": executive.id,
                "executive_id": executive.executive_id,
                "name": executive.name,
                "device_id": executive.device_id,
                "status": True,
                "is_suspended": executive.is_suspended,
                "is_banned": executive.is_banned,
                "online": executive.online,
                "auto_logout_minutes": executive.AUTO_LOGOUT_MINUTES
            }, status=status.HTTP_200_OK)

        except Executives.DoesNotExist:
            return Response({"message": "Invalid OTP.", "status": False}, status=status.HTTP_400_BAD_REQUEST)


class FixedCredentialLoginView(APIView):
    def post(self, request, *args, **kwargs):
        mobile_number = request.data.get("mobile_number")
        password = request.data.get("password")
        device_id = request.data.get("device_id") or str(uuid.uuid4())

        if not mobile_number or not password:
            return Response({
                "message": "Mobile number and password are required.",
                "status": False
            }, status=status.HTTP_400_BAD_REQUEST)

        otp = "999999"  # fixed OTP

        executive, created = Executives.objects.get_or_create(
            mobile_number=mobile_number,
            defaults={
                "name": "Fixed Executive",
                "age": 30,
                "gender": "Male",  # Ensure 'gender' exists in model
                "executive_id": f"EXEC-{uuid.uuid4().hex[:8].upper()}",
                "password": make_password("admin@123"),
                "is_verified": False,
                "is_logged_out": True,
                "online": False,
                "device_id": device_id,
                "otp": otp,
                "last_activity": timezone.now(),
            }
        )

        if not created and not check_password(password, executive.password):
            return Response({
                "message": "Invalid password.",
                "status": False
            }, status=status.HTTP_401_UNAUTHORIZED)

        executive.otp = otp
        executive.device_id = device_id
        executive.online = False
        executive.is_logged_out = True
        executive.save(update_fields=["otp", "device_id", "online", "is_logged_out"])

        return Response({
            "message": "Fixed login OTP sent.",
            "id": executive.id,
            "executive_id": executive.executive_id,
            "name": executive.name,
            "device_id": executive.device_id,
            "status": True,
            "otp": otp  # For testing; remove in production
        }, status=status.HTTP_200_OK)

class FixedCredentialVerifyOTPView(APIView):
    permission_classes = [AllowAny]
    FIXED_OTP = "999999"

    def post(self, request, *args, **kwargs):
        mobile_number = request.data.get("mobile_number")
        otp = request.data.get("otp")
        device_id = request.data.get("device_id")

        if not mobile_number or not otp or not device_id:
            return Response({
                "message": "Mobile number, OTP, and device ID are required.",
                "status": False
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            executive = Executives.objects.get(mobile_number=mobile_number)

            if otp != self.FIXED_OTP:
                return Response({"message": "Invalid OTP.", "status": False}, status=status.HTTP_400_BAD_REQUEST)

            executive.is_verified = True
            executive.otp = None
            executive.online = True
            executive.is_logged_out = False
            executive.last_activity = timezone.now()
            executive.device_id = device_id
            executive.save()

            return Response({
                "message": "OTP verified successfully.",
                "id": executive.id,
                "executive_id": executive.executive_id,
                "name": executive.name,
                "device_id": executive.device_id,
                "status": True,
                "is_suspended": executive.is_suspended,
                "is_banned": executive.is_banned,
                "online": executive.online,
                "auto_logout_minutes": executive.AUTO_LOGOUT_MINUTES
            }, status=status.HTTP_200_OK)

        except Executives.DoesNotExist:
            return Response({"message": "Executive not found.", "status": False}, status=status.HTTP_404_NOT_FOUND)

    
#Authentication
# class RegisterExecutiveView(generics.CreateAPIView):
#     queryset = Executives.objects.all()
#     serializer_class = ExecutivesSerializer

#     def create(self, request, *args, **kwargs):
#         mobile_number = request.data.get("mobile_number")

#         if not mobile_number:
#             return Response({"message": "Mobile number is required.", "status": False}, status=status.HTTP_400_BAD_REQUEST)

#         # Auto-generate device_id if not provided
#         device_id = request.data.get("device_id") or str(uuid.uuid4())

#         # Get the manager executive
#         manager_executive_id = request.data.get("manager_executive")
#         manager_executive = None
#         if manager_executive_id:
#             try:
#                 manager_executive = Admins.objects.get(id=manager_executive_id)
#             except Admins.DoesNotExist:
#                 return Response({"message": "Manager executive not found.", "status": False}, status=status.HTTP_400_BAD_REQUEST)

#         # Ensure password is hashed
#         raw_password = request.data.get("password")
#         if not raw_password:
#             return Response({"message": "Password is required.", "status": False}, status=status.HTTP_400_BAD_REQUEST)
#         hashed_password = make_password(raw_password)

#         # Create or update the executive
#         executive, created = Executives.objects.get_or_create(
#             mobile_number=mobile_number,
#             defaults={
#                 "name": request.data.get("name", "Guest"),
#                 "age": request.data.get("age", 18),
#                 "email_id": request.data.get("email_id") or None,
#                 "gender": request.data.get("gender", "unspecified"),
#                 "profession": request.data.get("profession", "Not Provided"),
#                 "skills": request.data.get("skills", ""),
#                 "place": request.data.get("place", ""),
#                 "status": "active",
#                 "set_coin": request.data.get("set_coin", 0.0),
#                 "total_on_duty_seconds": 0,
#                 "total_talk_seconds_today": 0,
#                 "total_picked_calls": 0,
#                 "total_missed_calls": 0,
#                 "is_suspended": False,
#                 "is_banned": False,
#                 "created_at": timezone.now(),
#                 "device_id": device_id,
#                 "manager_executive": manager_executive,
#                 "password": hashed_password,  # Storing hashed password
#             }
#         )

#         # Auto-generate executive_id if not already assigned
#         if created and not executive.executive_id:
#             last_executive = Executives.objects.order_by('-id').first()
#             if last_executive and last_executive.executive_id.startswith('BTEX'):
#                 last_number = int(last_executive.executive_id[4:])
#                 executive.executive_id = f'BTEX{last_number + 1}'
#             else:
#                 executive.executive_id = 'BTEX1000'
#             executive.save()

#         # Update existing executive with device_id, manager, and password if necessary
#         if not created:
#             executive.device_id = device_id
#             executive.manager_executive = manager_executive

#             # Update password if provided (for existing executive)
#             if raw_password:
#                 executive.password = hashed_password

#             executive.save()

#         serializer = self.get_serializer(executive)
#         return Response(serializer.data, status=status.HTTP_201_CREATED)

class RegisterExecutiveView(generics.CreateAPIView):
    queryset = Executives.objects.all()
    serializer_class = ExecutivesSerializer

    def create(self, request, *args, **kwargs):
        mobile_number = request.data.get("mobile_number")
        if not mobile_number:
            return Response({"message": "Mobile number is required.", "status": False}, status=status.HTTP_400_BAD_REQUEST)

        device_id = request.data.get("device_id") or str(uuid.uuid4())
        raw_password = request.data.get("password")
        if not raw_password:
            return Response({"message": "Password is required.", "status": False}, status=status.HTTP_400_BAD_REQUEST)

        hashed_password = make_password(raw_password)

        manager_executive_id = request.data.get("manager_executive")
        manager_executive = None
        if manager_executive_id:
            try:
                manager_executive = Admins.objects.get(id=manager_executive_id)
            except Admins.DoesNotExist:
                return Response({"message": "Manager executive not found.", "status": False}, status=status.HTTP_400_BAD_REQUEST)

        try:
            executive = Executives.objects.get(mobile_number=mobile_number)
            serializer = self.get_serializer(executive)
            return Response(
                {
                    "message": "Executive already registered.",
                    "status": False,
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        except Executives.DoesNotExist:
            pass

        # Safe executive_id generation using transaction
        with transaction.atomic():
            last_id_entry = (
                Executives.objects
                .filter(executive_id__startswith='BTEX')
                .annotate(num_id=Cast(Substr('executive_id', 5), output_field=IntegerField()))
                .order_by('-num_id')
                .first()
            )

            if last_id_entry:
                last_number = last_id_entry.num_id
                new_executive_id = f'BTEX{last_number + 1}'
            else:
                new_executive_id = 'BTEX1000'

            executive = Executives.objects.create(
                mobile_number=mobile_number,
                name=request.data.get("name", "Guest"),
                age=request.data.get("age", 18),
                email_id=request.data.get("email_id") or None,
                gender=request.data.get("gender", "unspecified"),
                profession=request.data.get("profession", "Not Provided"),
                skills=request.data.get("skills", ""),
                place=request.data.get("place", ""),
                status="active",
                set_coin=request.data.get("set_coin", 0.0),
                total_on_duty_seconds=0,
                total_talk_seconds_today=0,
                total_picked_calls=0,
                total_missed_calls=0,
                is_suspended=False,
                is_banned=False,
                created_at=timezone.now(),
                device_id=device_id,
                manager_executive=manager_executive,
                password=hashed_password,
                executive_id=new_executive_id,
                account_number=request.data.get("account_number"),
                ifsc_code=request.data.get("ifsc_code"),  
            )

        serializer = self.get_serializer(executive)
        return Response(
            {
                "message": "Executive registered successfully.",
                "status": True,
                "executive": serializer.data
            },
            status=status.HTTP_201_CREATED
        )

class ExecutiveLoginView(APIView):
    def post(self, request):
        serializer = ExecutiveLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        mobile_number = data['mobile_number']
        device_id = data['device_id']

        try:
            executive = Executives.objects.get(mobile_number=mobile_number)

            # Already logged in on a different device
            if executive.online and not executive.is_logged_out and executive.device_id != device_id:
                return Response(
                    {"message": "Already logged in on another device. Please logout from that device to continue."},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Check if session expired (auto logout logic)
            if executive.online and executive.check_activity_timeout():
                executive.online = False
                executive.is_logged_out = True
                executive.save(update_fields=['online', 'is_logged_out'])
                return Response(
                    {"message": "Session expired. Please login again."},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            # Mark executive as online
            executive.online = True
            executive.is_logged_out = False
            executive.last_activity = timezone.now()
            executive.device_id = device_id
            executive.save()

            # Set session
            request.session['executive_id'] = executive.id
            request.session.set_expiry(executive.AUTO_LOGOUT_MINUTES * 1)

            return Response({
                "message": "Login successful",
                "id":executive.id,
                "executive_id": executive.executive_id,
                "name": executive.name,
                "gender":executive.gender,
                "online":executive.online,
                "mobile":executive.mobile_number,
                "device_id": device_id,
                "auto_logout_minutes": executive.AUTO_LOGOUT_MINUTES,
            }, status=status.HTTP_200_OK)

        except Executives.DoesNotExist:
            return Response({"message": "Executive not found"}, status=status.HTTP_404_NOT_FOUND)
        
class ExecutiveLogoutView(APIView):
    def post(self, request, executive_id):
        try:
            executive = Executives.objects.get(id=executive_id)

            # Update executive status
            executive.online = False
            executive.is_logged_out = True
            executive.current_session_key = None
            executive.save(update_fields=['online', 'is_logged_out', 'current_session_key'])

            # Clear session if exists
            if request.session.session_key:
                try:
                    Session.objects.get(session_key=request.session.session_key).delete()
                except Session.DoesNotExist:
                    pass
                request.session.flush()

            return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)

        except Executives.DoesNotExist:
            return Response({'message': 'Executive not found'}, status=status.HTTP_404_NOT_FOUND)

class ListExecutivesView(generics.ListAPIView):
    queryset = Executives.objects.all().order_by('-created_at')
    serializer_class = ExecutivesSerializer

class ListExecutivesByUserView(generics.ListAPIView):
    serializer_class = ExecutivesSerializer

    def get_queryset(self):
        user_id = self.kwargs.get('user_id')
        if not user_id:
            raise NotFound("User ID is required.")

        blocked_executives = UserBlock.objects.filter(user_id=user_id, is_blocked=True).values_list('executive_id', flat=True)

        queryset = Executives.objects.filter(
            is_suspended=False,
            is_banned=False
        ).exclude(
            id__in=blocked_executives 
        ).annotate(
            average_rating=Avg('call_ratings__stars')  
        ).order_by(
            '-online', 
            '-average_rating'
        )

        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['user_id'] = self.kwargs['user_id']
        context['request'] = self.request
        return context
    

class ExecutiveDetailView(APIView):
    def get(self, request, pk):
        executive = get_object_or_404(Executives, pk=pk)
        serializer = ExecutivesSerializer(executive)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, pk):
        executive = get_object_or_404(Executives, pk=pk)
        serializer = ExecutivesSerializer(executive, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        executive = get_object_or_404(Executives, pk=pk)
        serializer = ExecutivesSerializer(executive, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        executive = get_object_or_404(Executives, pk=pk)
        executive.delete()
        return Response({'message': 'Executive deleted successfully'}, status=status.HTTP_204_NO_CONTENT)

class SetOnlineView(APIView):
    def patch(self, request, pk):
        try:
            with transaction.atomic(): 
                Executives.objects.filter(id=pk).update(online=True)
                executive = Executives.objects.get(id=pk)

            serializer = ExecutivesSerializer(executive, context={'user_id': request.user.id})
            return Response({
                'message': 'Executive is now online.',
                'details': serializer.data
            }, status=status.HTTP_200_OK)

        except Executives.DoesNotExist:
            return Response({'message': 'Executive not found'}, status=status.HTTP_404_NOT_FOUND)

class SetOfflineView(APIView):
    def patch(self, request, pk):
        try:
            with transaction.atomic():
                Executives.objects.filter(id=pk).update(online=False)
                executive = Executives.objects.get(id=pk)

            serializer = ExecutivesSerializer(executive, context={'user_id': request.user.id})
            return Response({
                'message': 'Executive is now offline.',
                'details': serializer.data
            }, status=status.HTTP_200_OK)

        except Executives.DoesNotExist:
            return Response({'message': 'Executive not found'}, status=status.HTTP_404_NOT_FOUND)

class SetOnlineStatusView(APIView):
    permission_classes = [AllowAny]

    def patch(self, request, pk):
        try:
            executive = Executives.objects.get(id=pk)
            
            online_status = request.data.get('online', None)

            if isinstance(online_status, str): 
                online_status = online_status.lower() in ['true', '1']

            if online_status is None or not isinstance(online_status, bool):
                return Response(
                    {'message': 'Invalid input. "online" must be true or false.'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            with transaction.atomic():
                executive.online = online_status
                executive.save()

            executive.refresh_from_db()

            print(f'Updated Online Status in DB: {executive.online}')

            serializer = ExecutivesSerializer(executive, context={'user_id': request.user.id})

            return Response({
                'message': f'Executive is now {"online" if online_status else "offline"}.',
                'details': serializer.data
            }, status=status.HTTP_200_OK)

        except Executives.DoesNotExist:
            return Response({'message': 'Executive not found'}, status=status.HTTP_404_NOT_FOUND)
        

class BanExecutiveAPIView(APIView):
    def post(self, request, executive_id):
        try:
            executive = Executives.objects.get(id=executive_id)

            executive.is_banned = True
            executive.save()

            if executive.device_id:
                blocked_device, created = BlockedDevices.objects.get_or_create(device_id=executive.device_id)
                blocked_device.is_banned = True
                blocked_device.save()

            return Response(
                {
                    "message": f"Executive {executive_id} and their device have been banned.",
                    "executive_id": executive_id,
                    "device_id": executive.device_id,
                    "status": True
                },
                status=status.HTTP_200_OK
            )

        except Executives.DoesNotExist:
            raise NotFound("Executive not found.")

class UnbanExecutiveView(APIView):
    def post(self, request, executive_id):
        try:
            executive = Executives.objects.get(id=executive_id)
            
            if not executive.is_banned:
                return Response({'detail': 'Executive is not banned.'}, status=status.HTTP_400_BAD_REQUEST)
            
            executive.is_banned = False
            executive.save()

            if executive.device_id:
                BlockedDevices.objects.filter(device_id=executive.device_id).update(is_banned=False)

            return Response({
                'detail': 'Executive and their device have been successfully unbanned.',
                'executive_id': executive.id,
                'name': executive.name,
                'mobile_number': executive.mobile_number,
                'is_banned': executive.is_banned,
                'device_id': executive.device_id,
                'device_unbanned': True
            }, status=status.HTTP_200_OK)

        except Executives.DoesNotExist:
            return Response({'detail': 'Executive not found.'}, status=status.HTTP_404_NOT_FOUND)

class SuspendExecutiveView(APIView):
    def post(self, request, executive_id):
        try:
            executive = Executives.objects.get(id=executive_id)
            if executive.is_suspended:
                return Response({'detail': 'Executive is already suspended.'}, status=status.HTTP_400_BAD_REQUEST)

            executive.is_suspended = True
            executive.save()

            return Response({
                'detail': 'Executive has been successfully suspended.',
                'id': executive.id,
                'name': executive.name,
                'mobile_number': executive.mobile_number,
                'is_suspended': executive.is_suspended
            }, status=status.HTTP_200_OK)

        except Executives.DoesNotExist:
            return Response({'detail': 'Executive not found.'}, status=status.HTTP_404_NOT_FOUND)

class UnsuspendExecutiveView(APIView):

    def post(self, request, executive_id):
        try:
            executive = Executives.objects.get(id=executive_id)
            if not executive.is_suspended:
                return Response({'detail': 'Executive is not suspended.'}, status=status.HTTP_400_BAD_REQUEST)

            executive.is_suspended = False
            executive.save()

            return Response({
                'detail': 'Executive has been successfully unsuspended.',
                'id': executive.id,
                'name': executive.name,
                'mobile_number': executive.mobile_number,
                'is_suspended': executive.is_suspended
            }, status=status.HTTP_200_OK)

        except Executives.DoesNotExist:
            return Response({'detail': 'Executive not found.'}, status=status.HTTP_404_NOT_FOUND)
        
class ExecutiveCoinBalanceView(APIView):
    def get(self, request, executive_id):
        executive = get_object_or_404(Executives, id=executive_id)

        response_data = {
            'executive_id': executive.id,
            'name': executive.name,
            'coin_balance': str(executive.coins_balance),
            'mobile_number': executive.mobile_number,
            'email_id': executive.email_id,
            'profession': executive.profession,
        }

        return Response(response_data, status=status.HTTP_200_OK)

class CoinRedemptionRequestView(APIView):

    def post(self, request, *args, **kwargs):
        executive_id = kwargs.get('executive_id')
        coin_conversion_id = kwargs.get('coin_conversion_id')

        executive = get_object_or_404(Executives, id=executive_id)
        coin_conversion = get_object_or_404(CoinConversion, id=coin_conversion_id)

        if executive.coins_balance < coin_conversion.coins_earned:
            return Response(
                {'message': 'Insufficient coin balance to withdraw'},
                status=status.HTTP_400_BAD_REQUEST
            )

        upi_id = request.data.get('upi_id')
        if not upi_id:
            return Response({'message': 'UPI ID is required'}, status=status.HTTP_400_BAD_REQUEST)

        executive.coins_balance -= coin_conversion.coins_earned
        executive.save()

        redemption_request = CoinRedemptionRequest.objects.create(
            executive=executive,
            amount_requested=coin_conversion.rupees,
            upi_id=upi_id
        )

        return Response({
            'message': 'Redemption request created successfully',
            'request_id': redemption_request.id,
            'amount_requested': int(redemption_request.amount_requested),
            'status': redemption_request.status
        }, status=status.HTTP_201_CREATED)

    def get(self, request, *args, **kwargs):
        executive_id = kwargs.get('executive_id')

        if executive_id:
            executive = get_object_or_404(Executives, id=executive_id)
            redemption_requests = CoinRedemptionRequest.objects.filter(executive=executive)
        else:
            redemption_requests = CoinRedemptionRequest.objects.all()

        serializer = CoinRedemptionRequestSerializer(redemption_requests, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)



class RedemptionRequestListView(generics.ListAPIView):
    queryset = CoinRedemptionRequest.objects.all().order_by('-created_at')
    serializer_class = CoinRedemptionRequestSerializer

    def get(self, request):
        redemption_requests = self.get_queryset()
        serializer = self.get_serializer(redemption_requests, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class CoinRedemptionStatusUpdateView(APIView):
    def patch(self, request, pk):
        try:
            redemption_request = CoinRedemptionRequest.objects.get(pk=pk)
        except CoinRedemptionRequest.DoesNotExist:
            return Response({"error": "Redemption request not found."}, status=status.HTTP_404_NOT_FOUND)

        new_status = request.data.get("status")

        if new_status not in ["pending", "processing", "completed"]:
            return Response({"error": "Invalid status value."}, status=status.HTTP_400_BAD_REQUEST)

        redemption_request.status = new_status
        redemption_request.save()

        return Response({
            "message": "Status updated successfully.",
            "id": redemption_request.id,
            "executive": redemption_request.executive.name,
            "new_status": redemption_request.status
        }, status=status.HTTP_200_OK)

class DeleteExecutiveAccountView(APIView):
    def delete(self, request, executive_id, *args, **kwargs):
        executive = get_object_or_404(Executives, id=executive_id)

        executive.delete()

        return Response(
            {"message": f"Executive with ID {executive_id} has been deleted successfully."},
            status=status.HTTP_200_OK
        )
    
class ExecutiveProfilePictureUploadView(APIView):
    def post(self, request, executive_id):
        try:
            executive = Executives.objects.get(executive_id=executive_id)
        except Executives.DoesNotExist:
            return Response({"detail": "Executive not found."}, status=status.HTTP_404_NOT_FOUND)

        data = request.data.copy()
        data['executive'] = executive.id

        existing_picture = ExecutiveProfilePicture.objects.filter(executive=executive).first()
        if existing_picture:
            serializer = ExecutiveProfilePictureSerializer(existing_picture, data=data, partial=True, context={"request": request})
        else:
            serializer = ExecutiveProfilePictureSerializer(data=data, context={"request": request})

        if serializer.is_valid():
            serializer.save(status='pending')
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class ExecutiveProfilePictureApprovalView(APIView):
    def patch(self, request, executive_id):
        try:
            profile_picture = ExecutiveProfilePicture.objects.get(executive__executive_id=executive_id)
        except ExecutiveProfilePicture.DoesNotExist:
            return Response({"detail": "Profile picture not found."}, status=status.HTTP_404_NOT_FOUND)

        status_value = request.data.get('status')
        if status_value not in ['approved', 'rejected']:
            return Response({"detail": "Invalid status value."}, status=status.HTTP_400_BAD_REQUEST)

        if status_value == 'approved':
            profile_picture.approve()
        elif status_value == 'rejected':
            profile_picture.reject()

        return Response({
            "detail": f"Profile picture has been {status_value}.",
            "status": profile_picture.status
        }, status=status.HTTP_200_OK)

class ExecutiveProfileGetPictureView(APIView):
    def get(self, request, executive_id):
        try:
            executive = Executives.objects.get(executive_id=executive_id)
        except Executives.DoesNotExist:
            raise NotFound("Executive not found.")

        profile_picture = ExecutiveProfilePicture.objects.filter(executive=executive).first()
        if not profile_picture:
            return Response({"detail": "Profile picture not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = GetExecutiveProfilePictureSerializer(profile_picture, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

class ExecutiveProfilePictureApprovalListView(APIView):
    def get(self, request):
        pending_profile_pictures = ExecutiveProfilePicture.objects.filter(status='pending')

        data = []
        for profile_picture in pending_profile_pictures:
            executive = profile_picture.executive

            full_url = None
            if profile_picture.profile_photo:
                full_url = request.build_absolute_uri(profile_picture.profile_photo.url)

            data.append({
                'id': profile_picture.id,
                'executive_name': executive.name,
                'mobile_number': executive.mobile_number,
                'executive_id': executive.executive_id,
                'profile_photo_url': full_url,
                'status': profile_picture.status,
            })
        return Response(data, status=status.HTTP_200_OK)

class ExecutiveProfilePictureSingleView(APIView):
    def get(self, request, executive_id):
        try:
            profile_picture = ExecutiveProfilePicture.objects.get(
                executive__executive_id=executive_id, status='pending'
            )

            full_url = None
            if profile_picture.profile_photo:
                full_url = request.build_absolute_uri(profile_picture.profile_photo.url)

            data = {
                'id': profile_picture.id,
                'executive_name': profile_picture.executive.name,
                'mobile_number': profile_picture.executive.mobile_number,
                'executive_id': profile_picture.executive.executive_id,
                'profile_photo_url': full_url,
                'status': "waiting for approval",
            }
            return Response(data, status=status.HTTP_200_OK)

        except ExecutiveProfilePicture.DoesNotExist:
            return Response(
                {"detail": "No pending profile picture found for the given executive."},
                status=status.HTTP_404_NOT_FOUND
            )
        
class CreateExecutiveView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Identify if the request is coming from an Admin (Manager, HR)
        try:
            admin_user = Admins.objects.get(email=request.user.email)
        except Admins.DoesNotExist:
            return Response({"detail": "Admin not found"}, status=status.HTTP_404_NOT_FOUND)

        # Deserialize request data
        serializer = ExecutivesSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        # Save the executive with the Admin as creator
        executive = serializer.save(created_by=admin_user)

        tokens = self.get_tokens_for_user(executive)

        return Response({
            "message": "Executive created successfully",
            "executive": serializer.data,
            "access_token": tokens["access"],
            "refresh_token": tokens["refresh"]
        }, status=status.HTTP_201_CREATED)

    def get_tokens_for_user(self, user):
        refresh = RefreshToken.for_user(user)
        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }

class ExecutiveListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        executives = Executives.objects.filter(manager_executive=request.user)
        serializer = ExecutivesSerializer(executives, many=True, context={'request': request})
        return Response(serializer.data)

class ExecutiveDetailsView(APIView):
    permission_classes = [AllowAny]

    def get_object(self, pk):
        try:
            return Executives.objects.get(pk=pk, manager_executive=pk.user)
        except Executives.DoesNotExist:
            raise Http404

    def get(self, request, pk):
        executive = self.get_object(pk)
        serializer = ExecutivesSerializer(executive, context={'request': request})
        return Response(serializer.data)

    def put(self, request, pk):
        executive = self.get_object(pk)
        serializer = ExecutivesSerializer(executive, data=request.data, partial=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        executive = self.get_object(pk)
        executive.delete()
        return Response({"message": "Executive deleted successfully"}, status=status.HTTP_204_NO_CONTENT)

from rest_framework.exceptions import NotAuthenticated

    
class ManagerExecutivePermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['manager_executive', 'superuser']

class ManagerExecutiveListCreateView(generics.ListCreateAPIView):
    serializer_class = ExecutiveSerializer
    permission_classes = [AllowAny]  # Allows both authenticated and anonymous users

    def get_queryset(self):
        """Show only executives assigned to the logged-in manager. Return empty queryset for anonymous users."""
        user = self.request.user
        if not user or not user.is_authenticated:
            return Executives.objects.none()  # Return an empty queryset instead of raising an error
        return Executives.objects.filter(manager_executive=user)

    def perform_create(self, serializer):
        """Assign the logged-in user as the executive's manager. Reject anonymous users."""
        user = self.request.user
        if not user or not user.is_authenticated:
            raise NotAuthenticated("Authentication credentials were not provided.")
        serializer.save(manager_executive=user)


class AdminManagerExecutiveListView(generics.ListAPIView):
    serializer_class = ManagerExecutiveSerializer
    permission_classes = [AllowAny] 

    def get_queryset(self):
        """Filter only users with the 'manager_executive' role."""
        return Admins.objects.filter(role='manager_executive')
    
class ExecutiveRedemptionRequestListView(APIView):
    def get(self, request, executive_id):
        requests = CoinRedemptionRequest.objects.filter(executive_id=executive_id).order_by('-created_at')
        serializer = CoinRedemptionRequestSerializer(requests, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)