from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from .models import *
from executives.models import *
from django.db.models import Avg
from .serializers import *
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.generics import RetrieveUpdateDestroyAPIView
from rest_framework import generics
from users.utils import send_otp_2factor
import random
from django.utils import timezone
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import NotFound
from calls.serializers import CallRatingSerializerview
from rest_framework.generics import RetrieveAPIView
from django.shortcuts import get_object_or_404
from calls.models import CallRating

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import random
from .models import User, ReferralCode, ReferralHistory, DeletedUser

class RegisterOrLoginView(APIView):
    def post(self, request, *args, **kwargs):
        mobile_number = request.data.get('mobile_number')
        referral_code = request.data.get('referral_code')
        otp = str(random.randint(100000, 999999))

        try:
            user = User.objects.get(mobile_number=mobile_number)

            if user.is_banned:
                return Response(
                    {'message': 'User is banned and cannot log in.', 'is_banned': True, 'is_existing_user': True},
                    status=status.HTTP_403_FORBIDDEN
                )

            try:
                send_otp_2factor(mobile_number, otp)
            except Exception as e:
                return Response(
                    {'message': 'Failed to send OTP. Please try again later.', 'message': str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            user.otp = otp
            user.save()

            if referral_code and not hasattr(user, 'referred_by'):
                try:
                    referrer = ReferralCode.objects.get(code=referral_code).user
                    ReferralHistory.objects.create(referrer=referrer, referred_user=user)
                except ReferralCode.DoesNotExist:
                    return Response(
                        {'message': 'Invalid referral code.', 'status': False},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            return Response(
                {
                    'message': 'Login OTP sent to your mobile number.',
                    'user_id': user.id,
                    'mobile_number':user.mobile_number,
                    'otp': user.otp,
                    'status': True,
                    'is_existing_user': True,
                    'user_main_id': user.user_id,
                },
                status=status.HTTP_200_OK
            )

        except User.DoesNotExist:
            # New code added here - check for deleted account
            has_deleted_account = DeletedUser.objects.filter(mobile_number=mobile_number).exists()
            initial_coin_balance = 0 if has_deleted_account else 300  # Set balance based on deletion history

            try:
                send_otp_2factor(mobile_number, otp)
            except Exception as e:
                return Response(
                    {'message': 'Failed to send OTP. Please try again later.', 'message': str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            # Modified to use initial_coin_balance instead of hardcoded 300
            user = User.objects.create(
                mobile_number=mobile_number,
                otp=otp,
                coin_balance=initial_coin_balance
            )

            if referral_code:
                try:
                    referrer = ReferralCode.objects.get(code=referral_code).user
                    ReferralHistory.objects.create(referrer=referrer, referred_user=user)
                except ReferralCode.DoesNotExist:
                    return Response(
                        {'message': 'Invalid referral code.', 'status': False},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            return Response(
                {
                    'message': 'Registration OTP sent to your mobile number.',
                    'status': True,
                    'is_existing_user': False,
                    'user_id': user.id,
                    'mobile_number':user.mobile_number,
                    'otp': user.otp,
                    'coin_balance': user.coin_balance,
                    'user_main_id': user.user_id,
                },
                status=status.HTTP_200_OK
            )

class DeleteUserAccountView(APIView):
    def delete(self, request, user_id, *args, **kwargs):
        user = get_object_or_404(User, id=user_id)
        
        DeletedUser.objects.get_or_create(mobile_number=user.mobile_number)
        
        user.delete()
        
        return Response(
            {"message": f"User with ID {user_id} has been deleted successfully."},
            status=status.HTTP_200_OK
        )

class VerifyOTPView(APIView):
    def post(self, request, *args, **kwargs):
        mobile_number = request.data.get('mobile_number')
        otp = request.data.get('otp')
        name = request.data.get('name') 
        gender = request.data.get('gender')

        try:
            user = User.objects.get(mobile_number=mobile_number, otp=otp)

            is_existing_user = user.is_verified

            user.otp = None
            user.is_verified = True

            if not is_existing_user and name and gender:
                user.name = name
                user.gender = gender
                user.save()

            user.save()

            return Response(
                {
                    'message': 'OTP verified successfully.',
                    'user_id': user.id,
                    'user_main_id': user.user_id,
                    'is_existing_user': is_existing_user
                },
                status=status.HTTP_200_OK
            )
        except User.DoesNotExist:
            return Response(
                {'message': 'Invalid mobile number or OTP.'},
                status=status.HTTP_400_BAD_REQUEST
            )

class GetUserCoinBalanceView(APIView):
    def get(self, request, user_id):
        user_profile = get_object_or_404(UserProfile, user_id=user_id)

        serializer = UserProfileSerializer(user_profile)
        return Response(serializer.data, status=status.HTTP_200_OK)

class UserListView(ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

class UserDetailView(RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    lookup_field = 'id'

    def perform_update(self, serializer):
        instance = serializer.save()
        instance.last_login = timezone.now()
        instance.save()

@api_view(['POST'])
def add_favourite(request, user_id, executive_id):
    try:
        executive = Executives.objects.get(id=executive_id)
        favourite, created = Favourite.objects.get_or_create(
            user_id=user_id,
            executive=executive
        )
        if created:
            return Response({'message': 'Favourite added successfully.'}, status=status.HTTP_201_CREATED)
        else:
            return Response({'message': 'Already favourited'}, status=status.HTTP_400_BAD_REQUEST)
    except Executives.DoesNotExist:
        return Response({'message': 'Executive not found'}, status=status.HTTP_404_NOT_FOUND)

class ListFavouritesView(ListAPIView):
    serializer_class = FavouriteSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        user_id = self.kwargs.get('user_id')
        return Favourite.objects.filter(user_id=user_id)

class RemoveFavouriteView(APIView):
    def delete(self, request, user_id, executive_id):
        print(f"Attempting to remove favourite for user_id: {user_id}, executive_id: {executive_id}")

        try:
            executive = Executives.objects.get(id=executive_id)
        except Executives.DoesNotExist:
            return Response({'message': 'Executive not found'}, status=status.HTTP_404_NOT_FOUND)

        try:
            favourite = Favourite.objects.get(user_id=user_id, executive=executive)
            favourite.delete()
            return Response({'message': 'Favourite removed successfully.'}, status=status.HTTP_200_OK)
        except Favourite.DoesNotExist:
            return Response({'message': 'Favourite not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
def get_ratings(request, executive_id):
    try:
        executive = Executives.objects.get(id=executive_id)
        ratings = Rating.objects.filter(executive=executive)
        serializer = RatingSerializer(ratings, many=True)
        return Response(serializer.data)
    except Executives.DoesNotExist:
        return Response({'message': 'Executive not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
def average_rating(request, executive_id):
    try:
        executive = Executives.objects.get(id=executive_id)
        average = Rating.objects.filter(executive=executive).aggregate(Avg('rating'))
        avg_rating = average['rating__avg'] or 0
        return Response({'average_rating': avg_rating}, status=status.HTTP_200_OK)
    except Executives.DoesNotExist:
        return Response({'message': 'Executive not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
def average_rating_all_executives(request):
    executives = Executives.objects.all()
    ratings = Rating.objects.values('executive').annotate(average_rating=Avg('rating'))

    avg_ratings = {rating['executive']: rating['average_rating'] for rating in ratings}

    data = []
    for executive in executives:
        data.append({
            'id': executive.id,
            'name': executive.name,
            'average_rating': avg_ratings.get(executive.id, 0)
        })

    return Response(data, status=status.HTTP_200_OK)

def get_object_or_404(model, **kwargs):
    try:
        return model.objects.get(**kwargs)
    except model.DoesNotExist:
        raise NotFound(f"{model.__name__} not found.")
    
class RateExecutiveView(APIView):
    def post(self, request, user_id, executive_id):
        try:
            executive = get_object_or_404(Executives, id=executive_id)
            if Rating.objects.filter(user_id=user_id, executive=executive).exists():
                return Response({'message': 'You have already rated this executive.'}, status=status.HTTP_400_BAD_REQUEST)

            data = request.data.copy()
            data['user'] = user_id
            data['executive'] = executive_id
            serializer = RatingSerializer(data=data)

            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except ValueError as ve:
            return Response({'message': str(ve)}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({'message': 'An unexpected error occurred.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        


class UserCoinBalanceView(APIView):
    def get(self, request, user_id):
        user = get_object_or_404(User, id=user_id)
        serializer = UserMaxCallTimeSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

class UserProfileDetailView(APIView):
    def get(self, request, user_id):
        user_profile = get_object_or_404(UserProfile, user_id=user_id)

        serializer = UserProfileSerializer(user_profile)

        return Response(serializer.data, status=status.HTTP_200_OK)

class CarouselImageListCreateView(APIView):
    def get(self, request):
        images = CarouselImage.objects.all()
        serializer = CarouselImageSerializer(images, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = CarouselImageSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CarouselImageDetailView(APIView):
    def get(self, request, image_id):
        try:
            image = CarouselImage.objects.get(id=image_id)
            serializer = CarouselImageSerializer(image)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except CarouselImage.DoesNotExist:
            return Response({'message': 'Image not found'}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, image_id):
        try:
            image = CarouselImage.objects.get(id=image_id)
            serializer = CarouselImageSerializer(image, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except CarouselImage.DoesNotExist:
            return Response({'message': 'Image not found'}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, image_id):
        try:
            image = CarouselImage.objects.get(id=image_id)
            image.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except CarouselImage.DoesNotExist:
            return Response({'message': 'Image not found'}, status=status.HTTP_404_NOT_FOUND)


class CareerListCreateView(generics.ListCreateAPIView):
    queryset = Career.objects.all()
    serializer_class = CareerSerializer

class CareerDetailView(generics.RetrieveAPIView):
    queryset = Career.objects.all()
    serializer_class = CareerSerializer
    lookup_field = 'id'

class BanUserAPIView(APIView):

    def post(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            user.is_banned = True
            user.save()
            return Response({"message": f"User {user_id} has been banned."})
        except User.DoesNotExist:
            raise NotFound("User not found")

class UnbanUserView(APIView):

    def post(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            if not user.is_banned:
                return Response({'detail': 'User is not banned.'}, status=status.HTTP_400_BAD_REQUEST)
            user.is_banned = False
            user.save()

            return Response({
                'detail': 'User has been successfully unbanned.',
                'id': user.id,
                'name': user.name,
                'mobile_number': user.mobile_number,
                'is_banned': user.is_banned
            }, status=status.HTTP_200_OK)

        except User.DoesNotExist:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

class SuspendUserView(APIView):

    def post(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            if user.is_suspended:
                return Response({'detail': 'User is already suspended.'}, status=status.HTTP_400_BAD_REQUEST)

            user.is_suspended = True
            user.save()

            return Response({
                'detail': 'User has been successfully suspended.',
                'id': user.id,
                'name': user.name,
                'mobile_number': user.mobile_number,
                'is_suspended': user.is_suspended
            }, status=status.HTTP_200_OK)

        except User.DoesNotExist:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

class UnsuspendUserView(APIView):

    def post(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            if not user.is_suspended:
                return Response({'detail': 'User is not suspended.'}, status=status.HTTP_400_BAD_REQUEST)

            user.is_suspended = False
            user.save()

            return Response({
                'detail': 'User has been successfully unsuspended.',
                'id': user.id,
                'name': user.name,
                'mobile_number': user.mobile_number,
                'is_suspended': user.is_suspended
            }, status=status.HTTP_200_OK)

        except User.DoesNotExist:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
        
class ReferralCodeByUserView(RetrieveAPIView):
    serializer_class = ReferralCodeSerializer

    def get_object(self):
        user_id = self.kwargs.get('user_id')
        try:
            return ReferralCode.objects.get(user_id=user_id)
        except ReferralCode.DoesNotExist:
            raise NotFound("Referral code not found for the given user ID.")

class UserExecutiveRatingsView(APIView):
    def get(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise NotFound(f"User with id {user_id} does not exist.")

        ratings = CallRating.objects.filter(user=user)

        serializer = CallRatingSerializerview(ratings, many=True)
        return Response(serializer.data)

class UserExecutiveTotalRatingsView(APIView):
    def get(self, request):
        users = User.objects.all()

        user_ratings_data = []
        for user in users:
            ratings = CallRating.objects.filter(user=user)
            serializer = CallRatingSerializerview(ratings, many=True)
            user_ratings_data.append({
                "user_id": user.id,
                "ratings": serializer.data
            })

        return Response(user_ratings_data, status=200)
    
class BlockUserAPIView(APIView):
    def post(self, request):
        user_id = request.data.get('user_id')
        executive_id = request.data.get('executive_id')
        reason = request.data.get('reason')

        if not user_id or not executive_id:
            return Response({'message': 'User ID and Executive ID are required.'}, status=status.HTTP_400_BAD_REQUEST)
        if not reason:
            return Response({'message': 'Reason is required to block the user.'}, status=status.HTTP_400_BAD_REQUEST)

        block_entry, created = UserBlock.objects.update_or_create(
            user_id=user_id,
            executive_id=executive_id,
            defaults={
                'is_blocked': True,
                'reason': reason
            }
        )

        message = 'User has been blocked successfully.'
        return Response({'message': message}, status=status.HTTP_200_OK)

class UnblockUserAPIView(APIView):
    def post(self, request):
        user_id = request.data.get('user_id')
        executive_id = request.data.get('executive_id')

        if not user_id or not executive_id:
            return Response({'message': 'User ID and Executive ID are required.'}, status=status.HTTP_400_BAD_REQUEST)

        block_entry, created = UserBlock.objects.update_or_create(
            user_id=user_id,
            executive_id=executive_id,
            defaults={
                'is_blocked': False,
                'reason': ''  
            }
        )

        message = 'User has been unblocked successfully.'
        return Response({'message': message}, status=status.HTTP_200_OK)

class BlockedUsersListAPIView(APIView):
    def get(self, request, executive_id):
        blocked_users = UserBlock.objects.filter(is_blocked=True, executive_id=executive_id)
        serializer = UserBlockListSerializer(blocked_users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
class UpdateDPImageView(APIView):
    permission_classes = [AllowAny]

    def patch(self, request):
        user = request.user
        serializer = UserDPImageSerializer(user, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(
                {"detail": "Profile picture updated successfully!", "dp_image": serializer.data['dp_image']},
                status=status.HTTP_200_OK,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class ReferralDetailsView(APIView):
    permission_classes = [] 

    def get(self, request, user_id):
        user = get_object_or_404(User, id=user_id)

        # Get referral code
        referral_code = ReferralCode.objects.filter(user=user).first()
        referral_code_data = ReferralCodeSerializer(referral_code).data if referral_code else None

        # Get referral history
        referral_history = ReferralHistory.objects.filter(referrer=user)
        referral_history_data = ReferralHistorySerializer(referral_history, many=True).data

        return Response({
            "user_id": user.id,
            "username": user.username,
            "referral_code": referral_code_data,
            "referral_history": referral_history_data
        }, status=status.HTTP_200_OK)