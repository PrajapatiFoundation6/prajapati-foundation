from django.contrib import admin

from .models import (
    ContactMessage,
    Donation,
    GalleryImage,
    News,
    StudentHelp,
    Volunteer,
)

admin.site.register(GalleryImage)
admin.site.register(StudentHelp)
admin.site.register(ContactMessage)


@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'published_date')
    list_filter = ('category',)
    search_fields = ('title', 'description')
    date_hierarchy = 'published_date'


@admin.register(Volunteer)
class VolunteerAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'approved', 'created')
    list_filter = ('approved',)
    actions = ['approve_volunteers']

    @admin.action(description="Mark selected volunteers as approved")
    def approve_volunteers(self, request, queryset):
        queryset.update(approved=True)


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ("name", "amount", "payment_id", "show_public", "created")
    list_filter = ("show_public",)
    search_fields = ("name", "email", "payment_id")
    readonly_fields = ("payment_id", "razorpay_order_id", "created")
