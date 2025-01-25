from datetime import timedelta, date
from django.contrib.auth import get_user_model, authenticate, login
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets, serializers
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny, BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView
from django.core.exceptions import ValidationError

from .models import (
    CustomUser, Room, Hall, Employee, BarAccount, RestaurantAccount, Reservation, Transaction, Payment, Notification,
    InventoryItem
)
from .serializers import (
    UserSerializer, RoomSerializer, HallSerializer, EmployeeSerializer, ReservationSerializer, BarAccountSerializer,
    RestaurantAccountSerializer, PaymentSerializer, TransactionSerializer, NotificationSerializer,
    InventoryItemSerializer
)
from .permissions import IsAdmin, IsStaff, IsGuest


class RoomViewSet(viewsets.ModelViewSet):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

    @action(detail=False, methods=['get'])
    def available_rooms(self, request):
        # Fetch rooms that are available for reservation
        available_rooms = Room.objects.filter(is_available=True)
        serializer = RoomSerializer(available_rooms, many=True)
        return Response(serializer.data)


class HallViewSet(viewsets.ModelViewSet):
    queryset = Hall.objects.all()
    serializer_class = HallSerializer
    permission_classes = [IsAuthenticated, IsAdmin]


class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer
    permission_classes = [IsAuthenticated, IsAdmin]


class BarAccountViewSet(viewsets.ModelViewSet):
    queryset = BarAccount.objects.all()
    serializer_class = BarAccountSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

    @action(detail=False, methods=['get'])
    def sales(self, request):
        sales = Transaction.objects.filter(account_type='bar').aggregate(Sum('amount'))
        return Response({'bar_sales': sales['amount__sum']}, status=status.HTTP_200_OK)


class RestaurantAccountViewSet(viewsets.ModelViewSet):
    queryset = RestaurantAccount.objects.all()
    serializer_class = RestaurantAccountSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

    @action(detail=False, methods=['get'])
    def sales(self, request):
        sales = Transaction.objects.filter(account_type='restaurant').aggregate(Sum('amount'))
        return Response({'restaurant_sales': sales['amount__sum']}, status=status.HTTP_200_OK)

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()  # Uses the default User model
        fields = ['id', 'username', 'email', 'password']

    def validate_email(self, value):
        # Ensure email is unique
        if get_user_model().objects.filter(email=value).exists():
            raise ValidationError("This email is already in use.")
        return value

    def create(self, validated_data):
        # Hash the password before saving
        user = get_user_model().objects.create_user(**validated_data)
        return user


class UserViewSet(viewsets.ModelViewSet):
    queryset = get_user_model().objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

    @action(detail=False, methods=['post'])
    def sign_up(self, request):
        """
        User registration endpoint.
        Requires email, username, and password.
        """
        serializer = UserSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Registration successful'}, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


    @action(detail=False, methods=['post'])
    def sign_in(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username, password=password)
        if user:
            login(request, user)
            return Response({'message': 'Login successful'}, status=status.HTTP_200_OK)
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)



class ReservationViewSet(viewsets.ModelViewSet):
    queryset = Reservation.objects.all()
    serializer_class = ReservationSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['post'])
    def check_in(self, request, pk=None):
        reservation = self.get_object()
        if reservation.status != 'confirmed':
            return Response({'error': 'Reservation must be confirmed before check-in'}, status=status.HTTP_400_BAD_REQUEST)
        reservation.status = 'checked_in'
        reservation.save()
        return Response({'status': 'checked in'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def check_out(self, request, pk=None):
        reservation = self.get_object()
        if reservation.status != 'checked_in':
            return Response({'error': 'Reservation must be checked in before check-out'}, status=status.HTTP_400_BAD_REQUEST)
        reservation.status = 'checked_out'
        reservation.save()
        return Response({'status': 'checked out'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def my_reservations(self, request):
        user_reservations = Reservation.objects.filter(guest=request.user)
        serializer = self.get_serializer(user_reservations, many=True)
        return Response(serializer.data)


class FinancialReportView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        bar_sales = Transaction.objects.filter(account_type='bar').aggregate(Sum('amount'))['amount__sum'] or 0
        restaurant_sales = Transaction.objects.filter(account_type='restaurant').aggregate(Sum('amount'))['amount__sum'] or 0
        reservation_sales = Payment.objects.aggregate(Sum('amount'))['amount__sum'] or 0

        overall_sales = bar_sales + restaurant_sales + reservation_sales
        return Response({
            'bar_sales': bar_sales,
            'restaurant_sales': restaurant_sales,
            'reservation_sales': reservation_sales,
            'overall_sales': overall_sales
        }, status=status.HTTP_200_OK)


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        # Automatically set the user who made the payment
        serializer.save(user=self.request.user)

    def get_queryset(self):
        # Allow users to only see their own payments unless they are admin
        if self.request.user.is_staff:
            return Payment.objects.all()
        return Payment.objects.filter(user=self.request.user)


class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Allow users to only see their own transactions unless they are admin
        if self.request.user.is_staff:
            return Transaction.objects.all()
        return Transaction.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        # Automatically set the user who made the transaction
        serializer.save(user=self.request.user)


class NotificationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        notifications = Notification.objects.filter(user=request.user)
        serializer = NotificationSerializer(notifications, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = NotificationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)  # Associate the notification with the logged-in user
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)


class InventoryItemViewSet(viewsets.ModelViewSet):
    queryset = InventoryItem.objects.all()
    serializer_class = InventoryItemSerializer
    permission_classes = [IsAuthenticated, IsAdmin]


class ReportViewSet(viewsets.ViewSet):
    @action(detail=False, methods=['get'])
    def reservation_report(self, request):
        total_reservations = Reservation.objects.count()
        active_reservations = Reservation.objects.filter(status='confirmed').count()

        data = {
            "total_reservations": total_reservations,
            "active_reservations": active_reservations,
        }
        return Response(data)

    @action(detail=False, methods=['get'])
    def revenue_report(self, request):
        total_revenue = Payment.objects.filter(payment_status='completed').aggregate(Sum('amount'))['amount__sum']

        data = {
            "total_revenue": total_revenue or 0.00
        }
        return Response(data)

    @action(detail=False, methods=['get'])
    def transaction_report(self, request):
        total_transactions = Transaction.objects.count()
        total_sales = Transaction.objects.aggregate(Sum('total_price'))['total_price__sum']

        data = {
            "total_transactions": total_transactions,
            "total_sales": total_sales or 0.00
        }
        return Response(data)

    @action(detail=False, methods=['get'])
    def reservation_details(self, request):
        reservations = Reservation.objects.all()
        reservations_data = ReservationSerializer(reservations, many=True).data

        data = {
            "reservations": reservations_data
        }
        return Response(data)
