from django.contrib import admin, messages
from django.shortcuts import render, redirect
from django.urls import path

from .models import (
    ContactMessage,
    Donation,
    GalleryImage,
    News,
    StudentHelp,
    Volunteer,
    GovScheme, SchemeUpdate,
)
from .forms import BulkGalleryUploadForm


@admin.register(GalleryImage)
class GalleryImageAdmin(admin.ModelAdmin):
    list_display = ("title", "uploaded_at")
    change_list_template = "admin/main/galleryimage/change_list.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("bulk-upload/", self.admin_site.admin_view(self.bulk_upload), name="galleryimage_bulk_upload"),
        ]
        return custom_urls + urls

    def bulk_upload(self, request):
        if request.method == "POST":
            title = request.POST.get("title", "").strip()
            files = request.FILES.getlist("images")

            if not title:
                messages.error(request, "Kripya title darj karein.")
            elif not files:
                messages.error(request, "Kripya kam se kam ek image select karein.")
            else:
                created = 0
                for f in files:
                    GalleryImage.objects.create(title=title, image=f)
                    created += 1
                messages.success(request, f"{created} images successfully upload ho gayi!")
                return redirect("admin:main_galleryimage_changelist")

        return render(request, "admin/main/galleryimage/bulk_upload.html", {})

admin.site.register(StudentHelp)
admin.site.register(ContactMessage)

@admin.register(GovScheme)
class GovSchemeAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "is_active", "priority", "updated_at")
    list_filter = ("category", "is_active")
    search_fields = ("name", "short_description")


@admin.register(SchemeUpdate)
class SchemeUpdateAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "published_date")
    list_filter = ("category",)
    search_fields = ("title",)


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
