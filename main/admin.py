from django.contrib import admin, messages
from django.shortcuts import render, redirect
from django.urls import path
from django.utils.html import format_html
from .models import (
    ContactMessage,
    Donation,
    GalleryImage,
    News,
    StudentHelp,
    Volunteer,
    GovScheme, SchemeUpdate,
    DonationProof,
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
@admin.register(DonationProof)
class DonationProofAdmin(admin.ModelAdmin):
    list_display = ("name", "amount", "phone", "transaction_id", "status", "wants_public", "show_public", "created")
    list_filter = ("status", "wants_public", "show_public")
    search_fields = ("name", "phone", "email", "transaction_id")
    readonly_fields = ("created", "screenshot_preview", "photo_preview")
    fields = ("status", "show_public", "admin_note", "name", "phone", "email", "amount",
              "transaction_id", "wants_public", "created", "screenshot_preview", "photo_preview")
    actions = ["verify_and_show", "verify_only", "reject"]

    @admin.display(description="Payment screenshot")
    def screenshot_preview(self, obj):
        if not obj.pk or not obj.screenshot:
            return "-"
        return format_html('<a href="{0}" target="_blank"><img src="{0}" style="max-height:420px;border-radius:8px"></a>', obj.screenshot.url)

    @admin.display(description="Donor photo")
    def photo_preview(self, obj):
        if not obj.pk or not obj.photo:
            return "-"
        return format_html('<img src="{}" style="max-height:160px;border-radius:50%">', obj.photo.url)

    @admin.action(description="Verify + list me dikhao (sirf jinhone permission di)")
    def verify_and_show(self, request, queryset):
        queryset.update(status="verified")
        shown = queryset.filter(wants_public=True).update(show_public=True)
        self.message_user(request, f"{queryset.count()} verified, {shown} list me dikhaye gaye.")

    @admin.action(description="Verify karo (list me mat dikhao)")
    def verify_only(self, request, queryset):
        queryset.update(status="verified", show_public=False)

    @admin.action(description="Reject karo")
    def reject(self, request, queryset):
        queryset.update(status="rejected", show_public=False)