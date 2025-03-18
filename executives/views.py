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
from datetime import timedelta
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

#OTPAUTH
class ExeRegisterOrLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        mobile_number = request.data.get('mobile_number')
        otp = generate_otp()

        try:
            # Check if the executive already exists
            executive = Executives.objects.get(mobile_number=mobile_number)

            # If executive is banned, deny access
            if executive.is_banned:
                return Response(
                    {'message': 'Executive is banned and cannot log in.', 'is_banned': True},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Send OTP for login
            if send_otp(mobile_number, otp):
                executive.otp = otp
                executive.save()
                return Response({
                    'message': 'Login OTP sent to your mobile number.',
                    'executive_id': executive.id,
                    'status': True,
                    'is_suspended': executive.is_suspended
                }, status=status.HTTP_200_OK)
            else:
                return Response(
                    {'message': 'Failed to send OTP. Please try again later.'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        except Executives.DoesNotExist:
            # Check if the request is from a manager_executive
            if not request.user.is_authenticated or request.user.role != 'manager_executive':
                return Response(
                    {'message': 'Only manager_executive can create new executives.'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Validate and create a new executive
            serializer = ExecutivesSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            if send_otp(mobile_number, otp):
                executive = serializer.save(otp=otp, created_by=request.user)
                return Response({
                    'message': 'Executive registered successfully. OTP sent to your mobile number.',
                    'executive_id': executive.id,
                    'status': True,
                    'is_suspended': False
                }, status=status.HTTP_201_CREATED)
            else:
                return Response(
                    {'message': 'Failed to send OTP. Please try again later.'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

class ExeVerifyOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        mobile_number = request.data.get('mobile_number')
        otp = request.data.get('otp')

        try:
            executive = Executives.objects.get(mobile_number=mobile_number, otp=otp)
            executive.otp = None
            executive.is_verified = True
            executive.save()
            return Response({'message': 'OTP verified successfully.', 'executive_id': executive.id},
                            status=status.HTTP_200_OK)
        except Executives.DoesNotExist:
            return Response({'message': 'Invalid mobile number or OTP.'},
                            status=status.HTTP_400_BAD_REQUEST)
#Authentication
class RegisterExecutiveView(generics.CreateAPIView):
    queryset = Executives.objects.all()
    serializer_class = ExecutivesSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class ExecutiveLoginView(APIView):
    def post(self, request):
        serializer = ExecutiveLoginSerializer(data=request.data)
        if serializer.is_valid():
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ListExecutivesView(generics.ListAPIView):
    queryset = Executives.objects.all()
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
            executive = Executives.objects.get(executive_id=executive_id)
            executive.is_banned = True
            executive.save()
            return Response({"message": f"Executive {executive_id} has been banned."})
        except Executives.DoesNotExist:
            raise NotFound("Executive not found")

class UnbanExecutiveView(APIView):
    def post(self, request, executive_id):
        try:
            executive = Executives.objects.get(executive_id=executive_id)
            if not executive.is_banned:
                return Response({'detail': 'Executive is not banned.'}, status=status.HTTP_400_BAD_REQUEST)
            executive.is_banned = False
            executive.save()

            return Response({
                'detail': 'Executive has been successfully unbanned.',
                'id': executive.id,
                'name': executive.name,
                'mobile_number': executive.mobile_number,
                'is_banned': executive.is_banned
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

    def post(self, request, executive_id, coin_conversion_id):
        executive = get_object_or_404(Executives, id=executive_id)
        coin_conversion = get_object_or_404(CoinConversion, id=coin_conversion_id)

        if executive.coins_balance < coin_conversion.coins_earned:
            return Response(
                {'error': 'Insufficient coin balance to withdraw'},
                status=status.HTTP_400_BAD_REQUEST
            )

        executive.coins_balance -= coin_conversion.coins_earned
        executive.save()

        redemption_request = CoinRedemptionRequest.objects.create(
            executive=executive,
            coin_conversion=coin_conversion,
            amount_requested=coin_conversion.rupees,
        )

        return Response({
            'message': 'Redemption request created successfully',
            'request_id': redemption_request.id,
            'amount_requested': float(redemption_request.amount_requested),
            'status': redemption_request.status
        }, status=status.HTTP_201_CREATED)

    def get(self, request, executive_id=None):
        if executive_id:
            executive = get_object_or_404(Executives, id=executive_id)
            redemption_requests = CoinRedemptionRequest.objects.filter(executive=executive)
        else:
            redemption_requests = CoinRedemptionRequest.objects.all()

        serializer = CoinRedemptionRequestSerializer(redemption_requests, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class RedemptionRequestListView(generics.ListAPIView):
    queryset = CoinRedemptionRequest.objects.all()
    serializer_class = CoinRedemptionRequestSerializer

    def get(self, request):
        redemption_requests = self.get_queryset()
        serializer = self.get_serializer(redemption_requests, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
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
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            admin_user = Admins.objects.get(user=request.user)  
        except Admins.DoesNotExist:
            return Response({"detail": "Admin not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = ExecutivesSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        executive = serializer.save(created_by=admin_user) 

        tokens = self.get_tokens_for_user(admin_user)

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
    permission_classes = [IsAuthenticated, IsManagerExecutive]

    def get(self, request):
        executives = Executives.objects.filter(created_by=request.user)
        serializer = ExecutivesSerializer(executives, many=True, context={'request': request})
        return Response(serializer.data)

class ExecutiveDetailsView(APIView):
    permission_classes = [IsAuthenticated, IsManagerExecutive]

    def get_object(self, pk):
        try:
            return Executives.objects.get(pk=pk, created_by=self.request.user)
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

    
class ManagerExecutivePermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['manager_executive', 'superuser']

class ManagerExecutiveListCreateView(generics.ListCreateAPIView):
    serializer_class = ExecutiveSerializer
    permission_classes = [ManagerExecutivePermission]

    def get_queryset(self):
        """Show only executives created by the logged-in manager."""
        return Executives.objects.filter(created_by=self.request.user)

    def perform_create(self, serializer):
        """Assign the logged-in user as the executive's manager."""
        serializer.save(created_by=self.request.user)