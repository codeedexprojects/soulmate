from .models import *
from .serializers import *
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import *
from .serializers import *
import random
from django.utils import timezone
from rest_framework.permissions import AllowAny
from django.db import transaction
from agora_token_builder import RtcTokenBuilder
import time
import uuid
from rest_framework import generics, viewsets,status
from django.shortcuts import get_object_or_404
import threading


AGORA_APP_ID = '9019fa33fc6d4654848121f4b88b346c'
AGORA_APP_CERTIFICATE = 'e2f0a6a085d34973ad08c7cfa785796d'

# 9626e8b8b5f847e6961cb9a996e1ae93
# ab41eb854807425faa1b44481ff97fe3
    
class CreateChannelView(APIView):
    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request):
        app_id = "9019ftiivkla33fc6d46548481241f4b88b564346c"
        app_certificate = "e2f0a6refa085d34973ad4676f08gttsxfc7cfa785796d"
        role = 1
        expiration_in_seconds = 3600

        channel_name = request.data.get("channel_name")
        executive_id = request.data.get("executive_id")
        user_id = request.data.get("user_id")

        if not channel_name:
            channel_name = f"bestie_{uuid.uuid4().hex[:8]}_{int(time.time())}"

        if not executive_id or not user_id:
            return Response({"error": "Both executive_id and user_id are required."}, status=400)

        try:
            # Lock the executive row to prevent race condition
            executive = Executives.objects.select_for_update().get(id=executive_id)
            user = User.objects.get(id=user_id)
        except Executives.DoesNotExist:
            return Response({"error": "Invalid executive_id."}, status=404)
        except User.DoesNotExist:
            return Response({"error": "Invalid user_id."}, status=404)

        if user.coin_balance < 180:
            return Response({"error": "Insufficient balance. You need at least 180 coins to start a call."}, status=403)

        if executive.on_call:
            return Response({"error": "The executive is already on another call."}, status=403)

        if not executive.online:
            return Response({"error": "The executive is offline."}, status=403)

        try:
            current_time = int(time.time())
            privilege_expired_ts = current_time + expiration_in_seconds

            user_token = RtcTokenBuilder.buildTokenWithUid(
                app_id, app_certificate, channel_name, user.id, role, privilege_expired_ts
            )
            executive_token = RtcTokenBuilder.buildTokenWithUid(
                app_id, app_certificate, channel_name, executive.id, 2, privilege_expired_ts
            )
        except Exception as e:
            return Response({"error": f"Token generation failed: {str(e)}"}, status=500)

        # Create call record
        call_history = AgoraCallHistory.objects.create(
            user=user,
            executive=executive,
            channel_name=channel_name,
            executive_token=executive_token,
            token=user_token,
            start_time=now(),
            executive_joined=False,
            uid=user.id,
            status="pending",
        )

        response_data = {
            "message": "Channel created successfully.",
            "token": user_token,
            "executive_token": executive_token,
            "channel_name": channel_name,
            "caller_name": user.name,
            "receiver_name": executive.name,
            "user_id": user.user_id,
            "executive_id": executive.executive_id,
            "executive": executive.id,
            "agora_uid": user.id,
            "executive_agora_uid": executive.id,
            "call_id": call_history.id
        }

        # Mark executive on_call AFTER sending response
        def mark_executive_on_call(executive_id):
            Executives.objects.filter(id=executive_id).update(on_call=True)

        threading.Thread(target=mark_executive_on_call, args=(executive.id,)).start()

        return Response(response_data, status=200)

    

class GetRecentChannelView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, executive_id):
        try:
            executive = Executives.objects.get(id=executive_id)
        except Executives.DoesNotExist:
            return Response({"error": "Invalid executive_id."}, status=404)

        recent_call = AgoraCallHistory.objects.filter(
            executive=executive
        ).order_by("-start_time").first()

        if recent_call:
            if recent_call.status != "pending":
                return Response({"message": "No new calls."}, status=202)

            return Response({
                "message": "Channel retrieved successfully.",
                "channel_name": recent_call.channel_name,
                "call_id": recent_call.id,
                "user_id": recent_call.user.user_id,
                "gender": recent_call.user.gender,
                "executive_token": recent_call.executive_token,
                "call_status": recent_call.status,  
            }, status=200)

        return Response({"message": "No recent channel found.","status":False}, status=404)


    
class ViewChannelForExecutiveView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        channel_name = request.query_params.get("channel_name")
        executive_id = request.query_params.get("executive_id")

        if not channel_name or not executive_id:
            return Response({"error": "Channel name and executive_id are required."}, status=400)

        try:
            executive = Executives.objects.get(id=executive_id)
        except Executives.DoesNotExist:
            return Response({"error": "Executive not found."}, status=404)

        call_entry = AgoraCallHistory.objects.filter(
            executive=executive,
            channel_name=channel_name,
            end_time=None,
        ).first()

        if call_entry:
            return Response({
                "message": "Executive already joined the channel.",
                "channel_name": channel_name,
                "executive_name": executive.name,
                "status": "joined",
                "agora_uid": executive.id,
            }, status=200)

        return Response({
            "message": "Channel created but executive hasn't joined yet.",
            "channel_name": channel_name,
            "executive_name": executive.name,
            "status": "not_joined",
            "agora_uid": executive.id,
        }, status=200)


from threading import Timer

class JoinChannelForExecutiveView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        channel_name = request.data.get("channel_name")
        executive_id = request.data.get("executive_id")
        token = request.data.get("token")

        if not channel_name or not executive_id or not token:
            return Response({"error": "Channel name, executive_id, and token are required."}, status=400)

        try:
            executive = Executives.objects.get(id=executive_id)
        except Executives.DoesNotExist:
            return Response({"error": "Executive not found."}, status=404)

        call_entry = AgoraCallHistory.objects.filter(
            channel_name=channel_name, executive=executive, end_time=None
        ).first()

        if not call_entry:
            return Response({"error": "Channel not found or already ended."}, status=404)

        Executives.objects.filter(id=executive.id).update(on_call=True)
        
        executive.refresh_from_db()  

        call_entry.executive_joined = True
        call_entry.status = "joined"
        call_entry.start_time = now()
        call_entry.save()

        return Response({
            "message": f"Executive {executive.name} successfully joined the channel.",
            "channel_name": channel_name,
            "executive_id": executive.id,
            "executive_name": executive.name,
            "status": "joined",
            "agora_uid": executive.id,
            "on_call": executive.on_call,  
            "call_id":call_entry.id
        }, status=200)

class GetCallStatusView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, call_id):
        try:
            call_history = AgoraCallHistory.objects.get(id=call_id)
        except AgoraCallHistory.DoesNotExist:
            return Response({"error": "Invalid call_id."}, status=404)

        return Response({
            "status": call_history.status,
            "executive_id": call_history.executive.id,
            "user_id": call_history.user.id,
            "gender": call_history.user.gender,
            "user":call_history.user.user_id,
            "token": call_history.token,
            "call_id": call_history.id,
            "executive_token": call_history.executive_token,
        }, status=200)
    
class LeaveChannelForExecutiveView(APIView):
    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request):
        call_id = request.data.get("call_id")

        if not call_id:
            return Response({"error": "Call ID is required."}, status=400)

        try:
            call_entry = AgoraCallHistory.objects.select_for_update().get(id=call_id)
        except AgoraCallHistory.DoesNotExist:
            return Response({"error": "Call history not found."}, status=404)

        if call_entry.status in ["left", "missed", "rejected"]:
            return Response({"error": f"Call already marked as {call_entry.status}."}, status=400)

        user = call_entry.user
        executive = call_entry.executive

        user.token_expiry = timezone.now()
        executive.token_expiry = timezone.now()
        user.save()
        executive.save()

        if call_entry.status == "pending":
            call_entry.status = "rejected"
            call_entry.end_time = now()
            call_entry.is_active = False
            call_entry.save()

            Executives.objects.filter(id=executive.id).update(on_call=False)
            executive.refresh_from_db()

            return Response({
                "message": f"Executive {executive.name} left the channel without joining.",
                "call_id": call_entry.id,
                "status": "rejected",
                "on_call": executive.on_call  
            }, status=200)

        if call_entry.status == "joined":
            call_entry.end_call()
            call_entry.status = "left"
            call_entry.save()

            Executives.objects.filter(id=executive.id).update(on_call=False)
            executive.refresh_from_db()

            return Response({
                "message": f"Executive {executive.name} has left the channel.",
                "call_id": call_entry.id,
                "status": "left",
                "on_call": executive.on_call  
            }, status=200)

        return Response({"error": "Unexpected call status."}, status=400)


class LeaveChannelForUserView(APIView):
    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request):
        call_id = request.data.get("call_id")

        if not call_id:
            return Response({"error": "Call ID is required."}, status=400)

        try:
            call_entry = AgoraCallHistory.objects.select_for_update().get(id=call_id)
        except AgoraCallHistory.DoesNotExist:
            return Response({"error": "Call history not found."}, status=404)

        if call_entry.status in ["left", "missed", "rejected"]:
            return Response({"error": f"Call already marked as {call_entry.status}."}, status=400)

        user = call_entry.user
        executive = call_entry.executive

        user.token_expiry = timezone.now()  
        executive.token_expiry = timezone.now()  
        user.save()
        executive.save()

        if call_entry.status == "pending":
            call_entry.status="missed"  
            call_entry.save()

            return Response({
                "message": f"Call was missed without joining.",
                "call_id": call_entry.id,
                "status": "missed",
            }, status=200)

        if call_entry.status == "joined":
            call_entry.end_call()  
            call_entry.status = "left"
            call_entry.save()
        
            Executives.objects.filter(id=executive.id).update(on_call=False)
            executive.refresh_from_db()

            return Response({
                "message": "Call ended successfully.",
                "call_id": call_entry.id,
                "status": "left",
                "call_duration": str(call_entry.duration),
                "coins_deducted": call_entry.coins_deducted,
                "coins_added": call_entry.coins_added,
            }, status=200)

        return Response({"error": "Unexpected call status."}, status=400)
        
class LeaveAllCallsForExecutiveView(APIView):
    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request):
        executive_id = request.data.get("executive_id")

        if not executive_id:
            return Response({"error": "Executive ID is required."}, status=400)

        try:
            executive = Executives.objects.get(id=executive_id)
        except Executives.DoesNotExist:
            return Response({"error": "Executive not found."}, status=404)

        ongoing_calls = AgoraCallHistory.objects.filter(executive=executive, end_time=None)

        if not ongoing_calls.exists():
            return Response({"message": "No ongoing calls found for this executive."}, status=404)

        executive.token_expiry = timezone.now()  
        executive.save()

        for call_entry in ongoing_calls:
            if call_entry.status == "pending":
                call_entry.status = "missed"
                call_entry.end_time = now()
                call_entry.save()

            elif call_entry.status == "joined":
                call_entry.status = "left"
                call_entry.end_time = now()
                call_duration = call_entry.end_time - call_entry.start_time
                call_entry.duration = call_duration

                user = call_entry.user
                total_seconds = int(call_duration.total_seconds())
                coins_to_deduct = total_seconds * 3  

                if user.coin_balance < coins_to_deduct:
                    coins_to_deduct = user.coin_balance  

                user.coin_balance -= coins_to_deduct
                executive.coins_balance += coins_to_deduct
                user.save()
                executive.save()

                call_entry.coins_deducted = coins_to_deduct
                call_entry.coins_added = coins_to_deduct
                call_entry.save()

        Executives.objects.filter(id=executive.id).update(on_call=False)
        executive.refresh_from_db()

        return Response({
            "message": f"All ongoing calls for executive {executive.name} have been ended.",
            "executive_name": executive.name,
            "executive_id": executive.id,
        }, status=200)

class ExeCallHistoryListView(generics.ListAPIView):
    serializer_class = ExeCallHistorySerializer

    def get_queryset(self):
        executive_id = self.kwargs['executive_id']
        return AgoraCallHistory.objects.filter(executive_id=executive_id)
    
class CallHistoryViewSet(viewsets.ModelViewSet):
    serializer_class = CallHistorySerializer
    queryset = AgoraCallHistory.objects.all()
    
    def get_queryset(self):
        # Check if the URL has a numeric component (user_id)
        if 'pk' in self.kwargs:
            user_id = self.kwargs['pk']
            return AgoraCallHistory.objects.filter(user_id=user_id).order_by('-start_time')
        return super().get_queryset()

    def retrieve(self, request, *args, **kwargs):
        # Override retrieve to return list when user_id is provided
        if 'pk' in kwargs:
            queryset = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
        return super().retrieve(request, *args, **kwargs)

class ExecutiveCallHistoryListView(APIView):
    def get(self, request, executive_id):
        executive = get_object_or_404(Executives, id=executive_id)

        call_histories = AgoraCallHistory.objects.filter(executive=executive)

        serializer = CallHistorySerializer(call_histories, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)
    
class OngoingCallsAPIView(APIView):

    def get(self, request):
        ongoing_calls = AgoraCallHistory.objects.filter(status='joined', end_time__isnull=True)

        ongoing_calls_data = []
        for call in ongoing_calls:
            duration = timezone.now() - call.start_time
            ongoing_calls_data.append({
                'call_id': call.id,
                'executive_name': call.executive.name,
                'user_id': call.user.user_id,
                'start_time': call.start_time,
                'duration_minutes': duration.total_seconds() / 60,
                'channel_name':call.channel_name,
                'token':call.executive_token,
                'uid':call.uid,
                'executive_id':call.executive.id,
            })

        return Response(ongoing_calls_data, status=status.HTTP_200_OK)