import enum

from django.db import models


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"


class AccountStatus(int, enum.Enum):
    ACTIVE = 1
    INACTIVE = 0
    PENDING = 2


class Account(models.Model):
    class Meta:
        db_table = "accounts"

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    description = models.CharField(max_length=255, null=True)
    status = models.IntegerField(choices=[(status.value, status.name) for status in AccountStatus])
    balance = models.FloatField()
    created_at = models.DateTimeField()


class User(models.Model):
    class Meta:
        db_table = "users"

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    age = models.IntegerField()
    email = models.CharField(max_length=255, null=True)
    role = models.CharField(max_length=255, choices=[(role.value, role.name) for role in UserRole])
    is_active = models.BooleanField()
    birth_date = models.DateField()
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="users")
