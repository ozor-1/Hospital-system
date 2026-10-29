from datetime import datetime, time, timedelta
from decimal import Decimal

from django.db.models import Count, Sum
from django.utils import timezone

from hospital.models import Appointment, Invoice, Patient, Payment, Visit

MRN = "HMS-000087"
today = timezone.localdate()
month_start = timezone.make_aware(datetime.combine(today.replace(day=1), time.min))
next_month_start = (month_start + timedelta(days=32)).replace(day=1)
this_monday = today - timedelta(days=today.weekday())
last_monday = this_monday - timedelta(days=7)

print("Today:", today)

print("\n1. Patients seen by each doctor this month")
q1 = (
    Visit.objects.filter(visit_at__gte=month_start, visit_at__lt=next_month_start)
    .values("doctor__user__last_name", "doctor__user__username")
    .annotate(patients=Count("patient", distinct=True))
    .order_by("-patients")
)
for row in q1:
    print(row)

print("\n2. Every visit for one patient, newest first")
q2 = Visit.objects.filter(patient__mrn=MRN).order_by("-visit_at")
for v in q2:
    print(v, "|", v.diagnosis)

print("\n3. How much one patient still owes")
billed = Invoice.objects.filter(visit__patient__mrn=MRN).aggregate(total=Sum("amount"))["total"] or Decimal("0")
paid = Payment.objects.filter(invoice__visit__patient__mrn=MRN).aggregate(total=Sum("amount"))["total"] or Decimal("0")
print("billed", billed, "paid", paid, "owes", billed - paid)

print("\n4. Today's appointments that haven't arrived yet")
q4 = Appointment.objects.filter(
    scheduled_at__date=today,
    status__in=[Appointment.Status.SCHEDULED, Appointment.Status.CONFIRMED],
).order_by("scheduled_at")
for a in q4:
    print(a)

print("\n5. No-shows last week (Monday to Sunday)", last_monday, "to", this_monday - timedelta(days=1))
q5 = Appointment.objects.filter(
    status=Appointment.Status.NO_SHOW,
    scheduled_at__date__gte=last_monday,
    scheduled_at__date__lt=this_monday,
).order_by("scheduled_at")
for a in q5:
    print(a)

print("\n6. Money collected this month")
print(Payment.objects.filter(paid_at__gte=month_start, paid_at__lt=next_month_start).aggregate(total=Sum("amount")))

print("\nSQL for query 2:")
print(q2.query)