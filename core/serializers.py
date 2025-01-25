#core/serializers.py
from datetime import date
from rest_framework import serializers
from .models import CustomUser, Transaction, InventoryItem, Reservation, Payment, Notification, Room, Hall, Employee, BarAccount, RestaurantAccount


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'role']


class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ['id', 'name', 'capacity', 'description', 'is_available', 'price']
        read_only_fields = ['id']

    def validate_capacity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Capacity must be greater than zero.")
        return value


class HallSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hall
        fields = ['id', 'name', 'capacity', 'description', 'is_available']
        read_only_fields = ['id']

    def validate_capacity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Capacity must be greater than zero.")
        return value


class EmployeeSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()  # To display the username instead of the user object

    class Meta:
        model = Employee
        fields = ['id', 'user', 'position', 'salary', 'hire_date']
        read_only_fields = ['id']

    def validate_salary(self, value):
        if value <= 0:
            raise serializers.ValidationError("Salary must be greater than zero.")
        return value


class BarAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = BarAccount
        fields = ['id', 'account_name', 'balance', 'password']
        read_only_fields = ['id', 'balance']  # Prevent balance from being updated directly


class RestaurantAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = RestaurantAccount
        fields = ['id', 'account_name', 'balance', 'password']
        read_only_fields = ['id', 'balance']  # Prevent balance from being updated directly


class InventoryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryItem
        fields = ['id', 'name', 'quantity', 'price', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def validate_quantity(self, value):
        if value < 0:
            raise serializers.ValidationError("Quantity cannot be negative.")
        return value

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Price cannot be negative.")
        return value

class TransactionSerializer(serializers.ModelSerializer):
    item = serializers.PrimaryKeyRelatedField(queryset=InventoryItem.objects.all())
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Transaction
        fields = ['id', 'item', 'quantity_sold', 'total_price', 'date']

    def validate(self, data):
        item = data.get('item')
        quantity_sold = data.get('quantity_sold')

        if item.quantity < quantity_sold:
            raise serializers.ValidationError(f"Only {item.quantity} items are available in stock.")
        return data

    def create(self, validated_data):
        item = validated_data.get('item')
        quantity_sold = validated_data.get('quantity_sold')

        # Deduct quantity from the inventory item
        item.quantity -= quantity_sold
        item.save()

        # Calculate the total price
        total_price = quantity_sold * item.price

        # Create the transaction
        transaction = Transaction.objects.create(
            item=item, quantity_sold=quantity_sold, total_price=total_price, date=validated_data.get('date')
        )

        return transaction

class ReservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reservation
        fields = [
            'id', 'guest_name', 'room', 'check_in_date', 'check_out_date', 'status', 'total_price'
        ]

    def validate(self, data):
        check_in_date = data.get('check_in_date')
        check_out_date = data.get('check_out_date')

        if check_in_date < date.today():
            raise serializers.ValidationError("Check-in date cannot be in the past.")

        if check_out_date <= check_in_date:
            raise serializers.ValidationError("Check-out date must be after check-in date.")

        return data

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['reservation', 'amount', 'payment_method', 'payment_status', 'payment_date']

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value

    def create(self, validated_data):
        payment = Payment.objects.create(**validated_data)

        # Logic to set payment status
        if payment.payment_method == 'cash' or payment.payment_method == 'mobile':
            payment.payment_status = 'completed'
        else:
            payment.payment_status = 'pending'  # Default for other payment methods

        payment.save()
        return payment

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'user', 'title', 'message', 'created_at', 'is_read']
        read_only_fields = ['id', 'created_at']

    def create(self, validated_data):
        notification = Notification.objects.create(**validated_data)
        return notification

class InventoryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryItem
        fields = '__all__'