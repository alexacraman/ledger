from django.db import models

class Customer(models.Model):
    name      = models.CharField(max_length=150)
    email     = models.EmailField(blank=True)
    phone     = models.CharField(max_length=50, blank=True)
    address   = models.TextField(blank=True)
    postcode  = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Supplier(models.Model):
    name     = models.CharField(max_length=150)
    email    = models.EmailField(blank=True)
    phone    = models.CharField(max_length=50, blank=True)
    address  = models.TextField(blank=True)
    postcode = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


