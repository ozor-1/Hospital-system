from hospital.models import Invoice

shown = 0
for inv in Invoice.objects.select_related("visit__patient"):
    if inv.balance > 0:
        print(inv.visit.patient.mrn, "owes", inv.balance)
        shown += 1
        if shown == 5:
            break