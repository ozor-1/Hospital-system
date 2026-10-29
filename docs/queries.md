# The six queries in Django

Run on 27 Oct 2026. The fake data is random, so another run gives different numbers.

Setup used by the queries:

```python
today = timezone.localdate()
month_start = timezone.make_aware(datetime.combine(today.replace(day=1), time.min))
next_month_start = (month_start + timedelta(days=32)).replace(day=1)
this_monday = today - timedelta(days=today.weekday())
last_monday = this_monday - timedelta(days=7)
```

## 1. How many patients did each doctor see this month?

```python
Visit.objects.filter(visit_at__gte=month_start, visit_at__lt=next_month_start) \
    .values("doctor__user__last_name", "doctor__user__username") \
    .annotate(patients=Count("patient", distinct=True)).order_by("-patients")
```

Result: {'doctor__user__last_name': 'Danjuma', 'doctor__user__username': 'doctor6', 'patients': 45}
{'doctor__user__last_name': 'Onyeama', 'doctor__user__username': 'doctor1', 'patients': 44}
{'doctor__user__last_name': 'Okafor', 'doctor__user__username': 'doctor3', 'patients': 44}
{'doctor__user__last_name': 'Nwosu', 'doctor__user__username': 'doctor5', 'patients': 43}
{'doctor__user__last_name': 'Etim', 'doctor__user__username': 'doctor2', 'patients': 41}
{'doctor__user__last_name': 'Adeyemi', 'doctor__user__username': 'doctor4', 'patients': 40}
Believable? yes

## 2. Every visit for one patient, newest first

```python
Visit.objects.filter(patient__mrn="HMS-000087").order_by("-visit_at")
```

Result: five visits for HMS-000087, on 29 Sep, 03 Sep, 13 Aug, 17 Jul and 30 Jun 2026, with diagnoses hypertension, peptic ulcer disease, skin infection, type 2 diabetes and hypertension.
Believable? yes

## 3. How much does one patient still owe?

```python
billed = Invoice.objects.filter(visit__patient__mrn="HMS-000087").aggregate(total=Sum("amount"))["total"] or Decimal("0")
paid = Payment.objects.filter(invoice__visit__patient__mrn="HMS-000087").aggregate(total=Sum("amount"))["total"] or Decimal("0")
billed - paid
```

Result: billed 186,500, paid 147,000, owes 39,500.
Believable? yes

## 4. Which of today's appointments haven't arrived yet?

```python
Appointment.objects.filter(
    scheduled_at__date=today,
    status__in=[Appointment.Status.SCHEDULED, Appointment.Status.CONFIRMED],
).order_by("scheduled_at")
```

Result: three appointments on 27 Oct: HMS-000228 at 13:15 (scheduled), HMS-000267 at 13:15 (confirmed), HMS-000011 at 13:45 (scheduled).
Believable? yes

## 5. Which appointments were no-shows last week?

"Last week" means the previous Monday to Sunday, 19 to 25 Oct 2026.

```python
Appointment.objects.filter(
    status=Appointment.Status.NO_SHOW,
    scheduled_at__date__gte=last_monday,
    scheduled_at__date__lt=this_monday,
).order_by("scheduled_at")
```

Result: 11 no-shows, between 19 and 22 Oct (HMS-000119 twice, then 000201, 000258, 000150, 000292, 000098, 000078, 000154, 000300, 000239).
Believable? yes

## 6. How much money was collected this month?

```python
Payment.objects.filter(paid_at__gte=month_start, paid_at__lt=next_month_start).aggregate(total=Sum("amount"))
```

Result: ₦8,238,500.
Believable? Yes

## The SQL Django ran (query 2)

```sql
SELECT "hospital_visit"."id", "hospital_visit"."patient_id", "hospital_visit"."doctor_id",
       "hospital_visit"."appointment_id", "hospital_visit"."visit_at", "hospital_visit"."reason",
       "hospital_visit"."note", "hospital_visit"."diagnosis"
FROM "hospital_visit"
INNER JOIN "hospital_patient" ON ("hospital_visit"."patient_id" = "hospital_patient"."id")
WHERE "hospital_patient"."mrn" = HMS-000087
ORDER BY "hospital_visit"."visit_at" DESC
```

## SQL comparison (query 2)

My Phase 1 SQL:

```sql
SELECT v.*
FROM visits v
JOIN patients p ON p.id = v.patient_id
WHERE p.mrn = 'HMS-000142'
ORDER BY v.visit_at DESC;
```

The SQL Django ran is shown above. (Django prints the MRN without quotes here. The real query sends it as a safe parameter.)



## SQL comparison (query 3)

My Phase 1 SQL used one query with a LEFT JOIN, SUM and GROUP BY.
In Django I ran two queries (total billed, total paid) and subtracted in Python.