from django.core.validators import FileExtensionValidator, MinValueValidator
from django.db import models

IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'png', 'webp']


class GalleryImage(models.Model):

    title = models.CharField(max_length=200)
    image = models.ImageField(
        upload_to='gallery/',
        validators=[FileExtensionValidator(IMAGE_EXTENSIONS)],
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.title


class Volunteer(models.Model):

    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    city = models.CharField(max_length=100)
    contribution = models.TextField()
    photo = models.ImageField(
        upload_to='volunteers/',
        validators=[FileExtensionValidator(IMAGE_EXTENSIONS)],
    )
    approved = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return self.name


class StudentHelp(models.Model):

    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=15)
    city = models.CharField(max_length=100)

    education_level = models.CharField(max_length=100, blank=True, default="")
    help_type = models.CharField(max_length=200, blank=True, default="")

    message = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class ContactMessage(models.Model):

    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class Donation(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField()
    amount = models.IntegerField()
    razorpay_order_id = models.CharField(max_length=200, blank=True, default="")
    payment_id = models.CharField(max_length=200, unique=True)
    show_public = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class News(models.Model):

    title = models.CharField(max_length=800)
    description = models.TextField(blank=True)
    image = models.URLField(blank=True)
    source_link = models.URLField(unique=True,max_length=800)
    category = models.CharField(max_length=100, blank=True, db_index=True)
    published_date = models.DateTimeField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-published_date']

    def __str__(self):
        return self.title
