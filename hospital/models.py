from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, Sum
from django.utils import timezone


def validate_date_of_birth(value):
    """Nobody is born in the future or is more than 120 years old."""
    today = timezone.localdate()
    if value > today:
        raise ValidationError("Date of birth cannot be in the future.")
    if value < today - timedelta(days=120 * 365):
        raise ValidationError("Date of birth is more than 120 years ago.")


class User(AbstractUser):
    """Django's login table. Deliberately empty: staff and patient details
    live in Staff and Patient."""

    pass


class Staff(models.Model):
    class Role(models.TextChoices):
        DOCTOR = "doctor", "Doctor"
        NURSE = "nurse", "Nurse"
        PHARMACIST = "pharmacist", "Pharmacist"
        RECEPTIONIST = "receptionist", "Receptionist"
        CASHIER = "cashier", "Cashier"
        ADMIN = "admin", "Admin"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="staff"
    )
    role = models.CharField(max_length=20, choices=Role.choices)
    phone = models.CharField(max_length=20, blank=True)

    class Meta:
        verbose_name_plural = "staff"

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.get_role_display()})"


class Patient(models.Model):
    class Sex(models.TextChoices):
        MALE = "male", "Male"
        FEMALE = "female", "Female"

    # Optional: only created when the patient signs up for the portal.
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="patient",
    )
    mrn = models.CharField(max_length=20, unique=True)  # number on the hospital card
    surname = models.CharField(max_length=100)
    first_name = models.CharField(max_length=100)
    date_of_birth = models.DateField(validators=[validate_date_of_birth])
    sex = models.CharField(max_length=10, choices=Sex.choices)
    phone = models.CharField(max_length=20, blank=True)
    address = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.mrn} - {self.surname} {self.first_name}"


class Appointment(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        CONFIRMED = "confirmed", "Confirmed"
        CHECKED_IN = "checked_in", "Checked in"
        IN_PROGRESS = "in_progress", "In progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
        NO_SHOW = "no_show", "No show"

    patient = models.ForeignKey(
        Patient, on_delete=models.PROTECT, related_name="appointments"
    )
    doctor = models.ForeignKey(
        Staff,
        on_delete=models.PROTECT,
        limit_choices_to={"role": "doctor"},
        related_name="appointments",
    )
    scheduled_at = models.DateTimeField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.SCHEDULED
    )
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        when = timezone.localtime(self.scheduled_at).strftime("%d %b %Y %H:%M")
        return f"{self.patient.mrn} on {when} ({self.get_status_display()})"


class Visit(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name="visits")
    doctor = models.ForeignKey(
        Staff,
        on_delete=models.PROTECT,
        limit_choices_to={"role": "doctor"},
        related_name="visits",
    )
    # Empty for walk-ins.
    appointment = models.OneToOneField(
        Appointment,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="visit",
    )
    visit_at = models.DateTimeField()
    reason = models.TextField()
    note = models.TextField(blank=True)
    diagnosis = models.TextField(blank=True)

    def clean(self):
        super().clean()
        if self.appointment_id and self.patient_id:
            if self.appointment.patient_id != self.patient_id:
                raise ValidationError(
                    "This appointment belongs to a different patient."
                )

    def __str__(self):
        when = timezone.localtime(self.visit_at).strftime("%d %b %Y %H:%M")
        return f"Visit of {self.patient.mrn} on {when}"


class Drug(models.Model):
    name = models.CharField(max_length=150, unique=True)

    def __str__(self):
        return self.name


class Prescription(models.Model):
    visit = models.ForeignKey(Visit, on_delete=models.PROTECT, related_name="prescriptions")
    drug = models.ForeignKey(Drug, on_delete=models.PROTECT, related_name="prescriptions")
    dose = models.CharField(max_length=100)
    frequency = models.CharField(max_length=100)
    duration = models.CharField(max_length=100, blank=True)
    instruction = models.TextField(blank=True)

    def __str__(self):
        return f"{self.drug} {self.dose}, {self.frequency}"


class Invoice(models.Model):
    visit = models.OneToOneField(Visit, on_delete=models.PROTECT, related_name="invoice")
    invoice_no = models.CharField(max_length=30, unique=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gt=0), name="invoice_amount_gt_0"
            )
        ]

    @property
    def amount_paid(self):
        return self.payments.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    @property
    def balance(self):
        return self.amount - self.amount_paid

    def __str__(self):
        return f"{self.invoice_no} (₦{self.amount})"


class Payment(models.Model):
    class Method(models.TextChoices):
        CASH = "cash", "Cash"
        TRANSFER = "transfer", "Transfer"
        POS = "pos", "POS"

    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name="payments")
    amount = models.DecimalField(max_digits=12, decimal_places=2)  # more than 0
    method = models.CharField(max_length=20, choices=Method.choices)
    reference = models.CharField(max_length=100, blank=True)
    paid_at = models.DateTimeField()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gt=0), name="payment_amount_gt_0"
            )
        ]

    def clean(self):
        super().clean()
        if self.invoice_id and self.amount is not None:
            already_paid = (
                self.invoice.payments.exclude(pk=self.pk).aggregate(total=Sum("amount"))["total"]
                or Decimal("0.00")
            )
            if already_paid + self.amount > self.invoice.amount:
                raise ValidationError(
                    f"Payments would exceed the invoice amount of ₦{self.invoice.amount} "
                    f"(already paid: ₦{already_paid})."
                )

    def __str__(self):
        return f"₦{self.amount} on {self.invoice}"