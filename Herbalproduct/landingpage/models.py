from django.db import models

# Create your models here.
class Customer(models.Model):
    email = models.EmailField(max_length=100, unique=True)
    username = models.CharField(max_length=50, unique=True)
    password = models.CharField(max_length=255)  # Django's make_password() outputs ~88+ chars
    address = models.CharField(max_length=200, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'customers'
    def __str__(self):
        return self.email