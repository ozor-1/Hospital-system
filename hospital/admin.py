from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import (
    Appointment,
    Drug,
    Invoice,
    Patient,
    Payment,
    Prescription,
    Staff,
    User,
    Visit,
)

admin.site.register(User, UserAdmin)


@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "phone")
    list_filter = ("role",)
    search_fields = ("user__username", "user__first_name", "user__last_name", "phone")
    list_select_related = ("user",)


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ("mrn", "surname", "first_name", "sex", "date_of_birth", "phone", "is_active")
    list_filter = ("sex", "is_active")
    search_fields = ("mrn", "surname", "first_name", "phone")
    ordering = ("surname", "first_name")


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("scheduled_at", "patient", "doctor", "status")
    list_filter = ("status", "doctor")
    search_fields = ("patient__mrn", "patient__surname", "patient__first_name")
    date_hierarchy = "scheduled_at"
    autocomplete_fields = ("patient",)
    list_select_related = ("patient", "doctor__user")


@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = ("visit_at", "patient", "doctor", "diagnosis")
    list_filter = ("doctor",)
    search_fields = ("patient__mrn", "patient__surname", "patient__first_name", "diagnosis")
    date_hierarchy = "visit_at"
    autocomplete_fields = ("patient", "appointment")
    list_select_related = ("patient", "doctor__user")


@admin.register(Drug)
class DrugAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ("visit", "drug", "dose", "frequency", "duration")
    list_filter = ("drug",)
    search_fields = ("drug__name", "visit__patient__mrn", "visit__patient__surname")
    autocomplete_fields = ("visit", "drug")
    list_select_related = ("visit__patient", "drug")


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("invoice_no", "visit", "amount", "balance", "created_at")
    search_fields = ("invoice_no", "visit__patient__mrn", "visit__patient__surname")
    date_hierarchy = "created_at"
    autocomplete_fields = ("visit",)
    list_select_related = ("visit__patient",)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("invoice", "amount", "method", "reference", "paid_at")
    list_filter = ("method",)
    search_fields = ("invoice__invoice_no", "reference", "invoice__visit__patient__mrn")
    date_hierarchy = "paid_at"
    autocomplete_fields = ("invoice",)
    list_select_related = ("invoice",)