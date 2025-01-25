from datetime import date
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser, User
from django.db import models
import uuid



class CustomUser(AbstractUser):
    role = models.CharField(
        max_length=50,
        choices=[('admin', 'Admin'), ('manager', 'Manager'), ('staff', 'Staff')],
    )
    groups = models.ManyToManyField(
        'auth.Group', related_name='customuser_set', blank=True
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission', related_name='customuser_permissions', blank=True
    )

    def __str__(self):
        return self.username


class Room(models.Model):
    number = models.CharField(max_length=10, unique=True)
    capacity = models.PositiveIntegerField()
    price_per_night = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()

    def __str__(self):
        return f"Room {self.number}"


class Hall(models.Model):
    name = models.CharField(max_length=100, unique=True)
    capacity = models.PositiveIntegerField()
    description = models.TextField(blank=True, null=True)
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class Employee(models.Model):
    user = models.OneToOneField(
        get_user_model(), on_delete=models.CASCADE, related_name='employee_profile'
    )
    position = models.CharField(max_length=100)
    salary = models.DecimalField(max_digits=10, decimal_places=2)
    hire_date = models.DateField()

    def __str__(self):
        return self.user.username


class BarAccount(models.Model):
    account_name = models.CharField(max_length=100, unique=True)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    password = models.CharField(max_length=128)

    def __str__(self):
        return self.account_name


class RestaurantAccount(models.Model):
    account_name = models.CharField(max_length=100, unique=True)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    password = models.CharField(max_length=128)

    def __str__(self):
        return self.account_name

class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=255)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"Notification for {self.user.username}: {self.title}"



class Reservation(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('checked_in', 'Checked In'),
        ('checked_out', 'Checked Out'),
    ]

    guest = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    check_in_date = models.DateField()
    check_out_date = models.DateField()
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending'
    )

    def is_active(self):
        today = date.today()
        return self.check_in_date <= today <= self.check_out_date

    def clean(self):
        if self.check_in_date < date.today():
            raise ValueError("Check-in date cannot be in the past.")
        if self.check_out_date <= self.check_in_date:
            raise ValueError("Check-out date must be after check-in date.")

    def __str__(self):
        return f"Reservation {self.id} - {self.guest.username} in Room {self.room.number}"

    def check_in(self):
        if self.status == 'confirmed':
            self.status = 'checked_in'
            self.save()

    def check_out(self):
        if self.status == 'checked_in':
            self.status = 'checked_out'
            self.save()


class InventoryItem(models.Model):
    name = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.quantity < 0:
            raise ValueError("Quantity cannot be negative.")
        if self.price < 0:
            raise ValueError("Price cannot be negative.")

    def __str__(self):
        return self.name


class Transaction(models.Model):
    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE)
    quantity_sold = models.PositiveIntegerField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.item.quantity < self.quantity_sold:
            raise ValueError("Not enough stock available for this transaction.")
        self.item.quantity -= self.quantity_sold
        self.item.save()
        self.total_price = self.quantity_sold * self.item.price
        super().save(*args, **kwargs)


class Payment(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('mobile', 'Mobile Payment'),
        ('card', 'Card Payment'),
    ]

    reservation = models.OneToOneField(Reservation, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(
        max_length=50, choices=PAYMENT_METHOD_CHOICES
    )
    payment_date = models.DateTimeField(auto_now_add=True)
    mobile_transaction_reference = models.CharField(
        max_length=255, null=True, blank=True
    )
    payment_status = models.CharField(max_length=50, default='pending')

    def clean(self):
        if self.amount <= 0:
            raise ValueError("Amount must be greater than zero.")

    def __str__(self):
        return f"Payment for Reservation {self.reservation.id} - {self.amount} TZS"

    def mark_as_paid(self):
        if self.payment_status == 'pending':
            self.payment_status = 'completed'
            self.save()


class CCTVLog(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    action = models.CharField(max_length=255)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    status = models.CharField(max_length=50, choices=[('entry', 'Entry'), ('exit', 'Exit')])

    def __str__(self):
        return f"CCTV Log for Room {self.room.number} - {self.action} at {self.timestamp}"


class OfflineData(models.Model):
    data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    synced = models.BooleanField(default=False)

    def __str__(self):
        return f"Offline Data entry created at {self.created_at}"


class KeyCard(models.Model):
    reservation = models.OneToOneField(Reservation, on_delete=models.CASCADE)
    key_card_code = models.CharField(max_length=255, unique=True)
    issued_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.key_card_code:
            self.key_card_code = str(uuid.uuid4())
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Key Card for Reservation {self.reservation.id}"


class RoomServiceOrder(models.Model):
    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE)
    description = models.TextField()
    status = models.CharField(max_length=50, choices=[('pending', 'Pending'), ('completed', 'Completed')])

    def __str__(self):
        return f"Room Service Order for Reservation {self.reservation.id}"



