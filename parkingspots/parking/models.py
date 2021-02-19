# Create your models here.
from django.db import models
from django.contrib.auth.models import User


class ParkingSpot(models.Model):
    name = models.IntegerField("ID", unique=True)
    lat = models.FloatField("Latitude")
    lon = models.FloatField("Longitude")
    reserved = models.IntegerField("Reserved", default = 0)

    def __int__(self):
    	return self.name


# {	
# 	"lat" : 37.7811,
# 	"lon" : -122.3965,
# 	"radius" : 1000
# } Testing with this .json file structure in postman




import uuid
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from users.models.actor import Actor
from django.utils.translation import ugettext_lazy as _
from stores.models.category import Category


class Product(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(verbose_name=_("Product Title"), max_length=300)
    description = models.TextField()
    category_id = models.ForeignKey(
        Category,
        verbose_name=_("Category label"),
        unique=False,
        related_name="category",
        on_delete=models.CASCADE,
    )
    price = models.FloatField(
        default=0.0,
        verbose_name=_("Price"),
    )
    is_visble = models.BooleanField(
        default=True,
        verbose_name=_("Visible"),
    )
    created_by = models.ForeignKey(
        Actor,
        verbose_name=_("Product Owner"),
        related_name="product_created_by",
        null=True,
        on_delete=models.CASCADE,
    )
    modified = models.DateTimeField(auto_now=True)
    publication_date = models.DateTimeField(
        verbose_name=_("Date Publication"), auto_now_add=True
    )
    start_date = models.DateTimeField(
        verbose_name=_("Start Date"), auto_now_add=True
    )
    # TODO
    training_duration = models.PositiveIntegerField(verbose_name=_("Trainig Duration"))
    access_duration = models.PositiveIntegerField(verbose_name=_("Access Duration"))

    modified_by = models.ForeignKey(
        Actor,
        verbose_name=_("Product Editor"),
        related_name="product_modified_by",
        null=True,
        on_delete=models.CASCADE,
    )

    class Meta:
        ordering = ("-publication_date",)
        verbose_name = _("Product")
        verbose_name_plural = _("Products")

    def __str__(self):
        return str(self.title)

