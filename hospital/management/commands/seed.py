import random
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import F, Sum
from django.utils import timezone

from hospital.models import (
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

STAFF_PASSWORD = "Staff12345!"

SURNAMES = [
    "Okafor", "Okeke", "Nwosu", "Eze", "Obi", "Onyeama", "Nnamdi", "Chukwu", "Uche", "Ibe",
    "Adeyemi", "Balogun", "Ogunleye", "Adebayo", "Afolabi", "Olawale", "Bello", "Fashola", "Akinola", "Ojo",
    "Abubakar", "Musa", "Ibrahim", "Danjuma", "Suleiman", "Yakubu", "Garba", "Lawal", "Usman", "Aliyu",
    "Udoh", "Etim", "Effiong", "Okon", "Bassey", "Ekpo", "Amadi", "Wike", "Briggs", "Ogbonna",
]
FIRST_NAMES_MALE = [
    "Chukwuemeka", "Ifeanyi", "Obinna", "Chidubem", "Emeka", "Tunde", "Segun", "Kunle", "Femi", "Babatunde",
    "Musa", "Abdullahi", "Sani", "Ibrahim", "Yusuf", "Emmanuel", "Chinedu", "Ikenna", "Uchenna", "Ayodele",
]
FIRST_NAMES_FEMALE = [
    "Ngozi", "Chioma", "Adaeze", "Ifeoma", "Nneka", "Funke", "Yetunde", "Bukola", "Folake", "Titilayo",
    "Aisha", "Fatima", "Zainab", "Hauwa", "Halima", "Blessing", "Grace", "Esther", "Amaka", "Oluchi",
]
STREETS = [
    "Ogui Road", "Zik Avenue", "Independence Layout", "Abakpa Road", "Ikeja Way", "Allen Avenue",
    "Ahmadu Bello Way", "Aba Road", "Rumuola Road", "Ring Road", "Wuse Close", "Opebi Street",
]
CITIES = ["Enugu", "Nsukka", "Lagos", "Abuja", "Onitsha", "Port Harcourt", "Ibadan", "Kano", "Awka", "Owerri"]
PHONE_PREFIXES = ["0803", "0806", "0810", "0813", "0814", "0816", "0701", "0802", "0805", "0807", "0811", "0815", "0901"]

# name, dose, frequency, duration, instruction
DRUGS = [
    ("Paracetamol", "500 mg", "Three times daily", "3 days", "Take after meals."),
    ("Artemether/Lumefantrine", "80/480 mg", "Twice daily", "3 days", "Take with food or milk."),
    ("Amoxicillin", "500 mg", "Three times daily", "5 days", "Complete the full course."),
    ("Ciprofloxacin", "500 mg", "Twice daily", "7 days", "Drink plenty of water."),
    ("Metronidazole", "400 mg", "Three times daily", "5 days", "Avoid alcohol."),
    ("Ibuprofen", "400 mg", "Twice daily", "5 days", "Take after meals."),
    ("Amlodipine", "5 mg", "Once daily", "30 days", "Take in the morning."),
    ("Metformin", "500 mg", "Twice daily", "30 days", "Take with meals."),
    ("Omeprazole", "20 mg", "Once daily", "14 days", "Take before breakfast."),
    ("Salbutamol inhaler", "2 puffs", "As needed", "30 days", "Rinse mouth after use."),
    ("Loratadine", "10 mg", "Once daily", "7 days", "May cause drowsiness."),
    ("Vitamin C", "500 mg", "Once daily", "14 days", ""),
    ("Ferrous sulphate", "200 mg", "Twice daily", "30 days", "Take with orange juice."),
    ("Oral rehydration salts", "1 sachet", "After each loose stool", "3 days", "Dissolve in 1 litre of clean water."),
    ("Diclofenac", "50 mg", "Twice daily", "5 days", "Take after meals."),
]
REASONS = [
    "Fever and headache", "Routine check-up", "Cough and catarrh", "Abdominal pain", "Follow-up visit",
    "High blood pressure review", "Body pains", "Diarrhoea and vomiting", "Skin rash", "Back pain",
    "Chest tightness", "Painful urination",
]
DIAGNOSES = [
    "Malaria", "Typhoid fever", "Hypertension", "Type 2 diabetes mellitus", "Upper respiratory tract infection",
    "Gastroenteritis", "Urinary tract infection", "Peptic ulcer disease", "Asthma", "Low back pain",
    "Skin infection", "Anaemia",
]
NOTES = [
    "Patient advised to rest and drink fluids.", "Review in two weeks.", "Blood tests requested.",
    "Patient counselled on diet.", "Vitals stable.", "Advised to return if symptoms persist.",
]

APPOINTMENT_STATUS = Appointment.Status


def local_dt(day, hour, minute):
    """A timezone-aware datetime on `day` at hour:minute, in the project's time zone (Lagos)."""
    return timezone.make_aware(datetime.combine(day, time(hour, minute)))


class Command(BaseCommand):
    help = "Fill the database with fake hospital data (safe to run more than once)"

    def add_arguments(self, parser):
        parser.add_argument("--seed", type=int, default=None, help="Fix the random seed to repeat a run.")

    def handle(self, *args, **options):
        self.rng = random.Random(options["seed"])
        self.stdout.write("Seeding...")
        with transaction.atomic():
            self.clear_old_data()
            self.now = timezone.now()
            self.today = timezone.localdate()
            self.create_staff()
            self.create_drugs()
            self.create_patients()
            self.create_appointments()
            self.create_visits()
            self.create_prescriptions()
            self.create_invoices_and_payments()
            self.check_rules()
        self.stdout.write(self.style.SUCCESS("Done."))
        self.stdout.write(
            f"Staff: {Staff.objects.count()}, patients: {Patient.objects.count()}, "
            f"drugs: {Drug.objects.count()}, appointments: {Appointment.objects.count()}, "
            f"visits: {Visit.objects.count()}, prescriptions: {Prescription.objects.count()}, "
            f"invoices: {Invoice.objects.count()}, payments: {Payment.objects.count()}"
        )
        self.stdout.write(f"Staff logins: doctor1 ... doctor6, receptionist1 ... receptionist3, cashier1, cashier2 (password: {STAFF_PASSWORD})")

    # ------------------------------------------------------------------ clean up
    def clear_old_data(self):
        # Children first. Every link is PROTECT, so deleting a parent that still has
        # children raises ProtectedError. Superusers are kept.
        Payment.objects.all().delete()
        Invoice.objects.all().delete()
        Prescription.objects.all().delete()
        Visit.objects.all().delete()
        Appointment.objects.all().delete()
        Patient.objects.all().delete()
        Staff.objects.all().delete()
        Drug.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()

    # ------------------------------------------------------------------ helpers
    def person_name(self, sex):
        first = self.rng.choice(FIRST_NAMES_MALE if sex == "male" else FIRST_NAMES_FEMALE)
        return self.rng.choice(SURNAMES), first

    def phone(self):
        return self.rng.choice(PHONE_PREFIXES) + "".join(str(self.rng.randint(0, 9)) for _ in range(7))

    # ------------------------------------------------------------------ staff
    def create_staff(self):
        plan = [
            (Staff.Role.DOCTOR, "doctor", 6),
            (Staff.Role.RECEPTIONIST, "receptionist", 3),
            (Staff.Role.CASHIER, "cashier", 2),
        ]
        for role, prefix, count in plan:
            for n in range(1, count + 1):
                sex = self.rng.choice(["male", "female"])
                surname, first = self.person_name(sex)
                user = User.objects.create_user(
                    username=f"{prefix}{n}",
                    password=STAFF_PASSWORD,
                    first_name=first,
                    last_name=surname,
                    email=f"{prefix}{n}@hospital.example",
                )
                Staff.objects.create(user=user, role=role, phone=self.phone())
        self.doctors = list(Staff.objects.filter(role=Staff.Role.DOCTOR))

    def create_drugs(self):
        Drug.objects.bulk_create([Drug(name=d[0]) for d in DRUGS])
        self.drugs = {d.name: d for d in Drug.objects.all()}

    # ------------------------------------------------------------------ patients
    def create_patients(self):
        patients = []
        for i in range(1, 301):
            sex = self.rng.choice(["male", "female"])
            surname, first = self.person_name(sex)
            age_days = self.rng.randint(0, 90 * 365)  # 0 to 90 years old, never in the future
            patients.append(
                Patient(
                    mrn=f"HMS-{i:06d}",
                    surname=surname,
                    first_name=first,
                    date_of_birth=self.today - timedelta(days=age_days),
                    sex=sex,
                    phone=self.phone(),
                    address=f"{self.rng.randint(1, 80)} {self.rng.choice(STREETS)}, {self.rng.choice(CITIES)}",
                )
            )
        Patient.objects.bulk_create(patients)
        self.patients = list(Patient.objects.order_by("mrn"))
        # created_at is auto_now_add, so it is "now" for everyone. Spread the
        # registration dates over the last 200 days (update() skips auto_now_add).
        for p in self.patients:
            p.created_at = self.now - timedelta(
                days=self.rng.randint(10, 200), hours=self.rng.randint(0, 23), minutes=self.rng.randint(0, 59)
            )
        Patient.objects.bulk_update(self.patients, ["created_at"])

    # ------------------------------------------------------------------ appointments
    def pick_slot(self, patient, day_from, day_to):
        """A random working-hours slot, after the patient registered, that is
        free for the doctor. day_from/day_to are day offsets from today."""
        while True:
            day = self.today + timedelta(days=self.rng.randint(day_from, day_to))
            if day.weekday() == 6:  # no clinics on Sunday
                continue
            when = local_dt(day, self.rng.randint(8, 16), self.rng.choice([0, 15, 30, 45]))
            doctor = self.rng.choice(self.doctors)
            if when <= patient.created_at + timedelta(days=1):
                continue
            if (doctor.pk, when) in self.taken:
                continue
            self.taken.add((doctor.pk, when))
            return doctor, when

    def make_appointment(self, patient, doctor, when, status):
        created = min(when - timedelta(days=self.rng.randint(1, 14), hours=self.rng.randint(0, 6)), self.now - timedelta(hours=1))
        created = max(created, patient.created_at + timedelta(minutes=5))
        appt = Appointment(
            patient=patient,
            doctor=doctor,
            scheduled_at=when,
            status=status,
            reason=self.rng.choice(REASONS) if self.rng.random() < 0.9 else "",
        )
        appt._planned_created_at = created
        return appt

    def create_appointments(self):
        self.taken = set()
        appts = []

        # About 800 in the last four months. Completed, no-show or cancelled.
        for _ in range(800):
            patient = self.rng.choice(self.patients)
            doctor, when = self.pick_slot(patient, -120, -1)
            status = self.rng.choices(
                [APPOINTMENT_STATUS.COMPLETED, APPOINTMENT_STATUS.NO_SHOW, APPOINTMENT_STATUS.CANCELLED],
                weights=[76, 12, 12],
            )[0]
            appts.append(self.make_appointment(patient, doctor, when, status))

        # Today: those whose time has passed mostly arrived and were seen; some
        # haven't arrived yet. Those still to come are booked.
        for _ in range(8):
            patient = self.rng.choice(self.patients)
            doctor, when = self.pick_slot(patient, 0, 0)
            if when > self.now:
                status = self.rng.choice([APPOINTMENT_STATUS.SCHEDULED, APPOINTMENT_STATUS.CONFIRMED])
            elif self.rng.random() < 0.8:
                status = APPOINTMENT_STATUS.COMPLETED
            else:
                status = self.rng.choice([APPOINTMENT_STATUS.SCHEDULED, APPOINTMENT_STATUS.CONFIRMED])
            appts.append(self.make_appointment(patient, doctor, when, status))

        # About 50 booked for the next two weeks.
        for _ in range(50):
            patient = self.rng.choice(self.patients)
            doctor, when = self.pick_slot(patient, 1, 14)
            status = self.rng.choice([APPOINTMENT_STATUS.SCHEDULED, APPOINTMENT_STATUS.CONFIRMED])
            appts.append(self.make_appointment(patient, doctor, when, status))

        planned = {(a.patient_id, a.doctor_id, a.scheduled_at): a._planned_created_at for a in appts}
        Appointment.objects.bulk_create(appts)
        self.appointments = list(Appointment.objects.select_related("patient", "doctor"))
        for a in self.appointments:
            a.created_at = planned[(a.patient_id, a.doctor_id, a.scheduled_at)]
        Appointment.objects.bulk_update(self.appointments, ["created_at"])

    # ------------------------------------------------------------------ visits
    def create_visits(self):
        visits = []
        # One visit for every appointment that was attended.
        for a in self.appointments:
            if a.status != APPOINTMENT_STATUS.COMPLETED:
                continue
            visit_at = min(a.scheduled_at + timedelta(minutes=self.rng.randint(0, 25)), self.now)
            visits.append(
                Visit(
                    patient=a.patient,
                    doctor=a.doctor,
                    appointment=a,
                    visit_at=visit_at,
                    reason=a.reason or self.rng.choice(REASONS),
                    note=self.rng.choice(NOTES) if self.rng.random() < 0.7 else "",
                    diagnosis=self.rng.choice(DIAGNOSES),
                )
            )
        # About 100 walk-ins in the last four months, no appointment.
        for _ in range(100):
            patient = self.rng.choice(self.patients)
            while True:
                day = self.today + timedelta(days=self.rng.randint(-120, -1))
                visit_at = local_dt(day, self.rng.randint(8, 17), self.rng.randint(0, 59))
                if day.weekday() != 6 and visit_at > patient.created_at:
                    break
            visits.append(
                Visit(
                    patient=patient,
                    doctor=self.rng.choice(self.doctors),
                    appointment=None,
                    visit_at=visit_at,
                    reason="Walk-in: " + self.rng.choice(REASONS),
                    note=self.rng.choice(NOTES) if self.rng.random() < 0.7 else "",
                    diagnosis=self.rng.choice(DIAGNOSES),
                )
            )
        Visit.objects.bulk_create(visits)
        self.visits = list(Visit.objects.select_related("patient").order_by("visit_at", "id"))

    # ------------------------------------------------------------------ prescriptions
    def create_prescriptions(self):
        rows = []
        for v in self.visits:
            for name in self.rng.sample(list(self.drugs), self.rng.randint(1, 3)):
                _, dose, frequency, duration, instruction = next(d for d in DRUGS if d[0] == name)
                rows.append(
                    Prescription(
                        visit=v, drug=self.drugs[name], dose=dose, frequency=frequency,
                        duration=duration, instruction=instruction,
                    )
                )
        Prescription.objects.bulk_create(rows)

    # ------------------------------------------------------------------ invoices and payments
    def split(self, total_units, parts):
        """Split a whole number into `parts` positive whole numbers."""
        if parts == 1:
            return [total_units]
        cuts = sorted(self.rng.sample(range(1, total_units), parts - 1))
        edges = [0] + cuts + [total_units]
        return [edges[i + 1] - edges[i] for i in range(parts)]

    def create_invoices_and_payments(self):
        invoices = []
        planned_created = {}
        for n, v in enumerate(self.visits, start=1):
            # Money as Decimal, in multiples of 500 naira, 5,000 to 60,000.
            amount = Decimal(self.rng.randrange(5000, 60001, 500))
            invoices.append(Invoice(visit=v, invoice_no=f"INV-{n:06d}", amount=amount))
            planned_created[v.pk] = min(v.visit_at + timedelta(minutes=self.rng.randint(20, 180)), self.now)
        Invoice.objects.bulk_create(invoices)
        self.invoices = list(Invoice.objects.order_by("invoice_no"))
        for inv in self.invoices:
            inv.created_at = planned_created[inv.visit_id]
        Invoice.objects.bulk_update(self.invoices, ["created_at"])

        payments = []
        for inv in self.invoices:
            units = int(inv.amount // 500)
            roll = self.rng.random()
            if roll < 0.68:      # paid in full, one payment
                parts = [units]
            elif roll < 0.80:    # paid in full, in two or three parts
                parts = self.split(units, self.rng.choice([2, 3]))
            elif roll < 0.90:    # part-paid: still owes something
                paid_units = self.rng.randint(1, units - 1)
                parts = self.split(paid_units, self.rng.choice([1, 2]) if paid_units >= 2 else 1)
            else:                # not paid at all
                parts = []
            paid_at = inv.created_at
            for i, part in enumerate(parts):
                paid_at = min(paid_at + timedelta(minutes=self.rng.randint(0, 30)) + timedelta(days=self.rng.randint(0, 20) if i else 0), self.now)
                method = self.rng.choice(Payment.Method.values)
                reference = ""
                if method == Payment.Method.TRANSFER:
                    reference = f"TRF{self.rng.randint(10**9, 10**10 - 1)}"
                elif method == Payment.Method.POS:
                    reference = f"POS-{self.rng.randint(10**5, 10**6 - 1)}"
                payments.append(
                    Payment(invoice=inv, amount=Decimal(part * 500), method=method, reference=reference, paid_at=paid_at)
                )
        Payment.objects.bulk_create(payments)

    # ------------------------------------------------------------------ safety net
    def check_rules(self):
        """Stop (and roll everything back) if the fake data breaks a hospital rule."""
        problems = []
        if Visit.objects.filter(appointment__status__in=["no_show", "cancelled"]).exists():
            problems.append("a no-show or cancelled appointment has a visit")
        if Appointment.objects.filter(scheduled_at__gt=self.now).exclude(status__in=["scheduled", "confirmed"]).exists():
            problems.append("a future appointment is not booked")
        if Visit.objects.filter(visit_at__lt=F("patient__created_at")).exists():
            problems.append("a visit happened before the patient registered")
        if Appointment.objects.filter(created_at__lt=F("patient__created_at")).exists():
            problems.append("an appointment was made before the patient registered")
        if Visit.objects.filter(visit_at__gt=self.now).exists():
            problems.append("a visit is in the future")
        if Payment.objects.filter(paid_at__gt=self.now).exists() or Payment.objects.filter(paid_at__lt=F("invoice__created_at")).exists():
            problems.append("a payment has a bad date")
        for inv in Invoice.objects.annotate(paid=Sum("payments__amount")):
            if (inv.paid or 0) > inv.amount:
                problems.append(f"{inv.invoice_no} is overpaid")
        today = timezone.localdate()
        if Patient.objects.filter(date_of_birth__gt=today).exists():
            problems.append("a patient was born in the future")
        if Patient.objects.filter(date_of_birth__lt=today - timedelta(days=120 * 365)).exists():
            problems.append("a patient is over 120 years old")
        if Visit.objects.exclude(appointment=None).exclude(appointment__patient=F("patient")).exists():
            problems.append("a visit's patient differs from its appointment's patient")
        if Invoice.objects.count() != Visit.objects.count():
            problems.append("not exactly one invoice per visit")
        if problems:
            raise CommandError("Fake data broke the rules: " + "; ".join(problems))
        