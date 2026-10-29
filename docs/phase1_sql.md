# My Phase 1 SQL (written by hand)

## 1. How many patients did each doctor see this month?

SELECT s.id, s.surname, COUNT(DISTINCT v.patient_id) AS patients_seen,
       COUNT(*) AS visits
FROM visits v
JOIN staff s ON s.id = v.doctor_id
WHERE v.visit_at >= date_trunc('month', now())
  AND v.visit_at < date_trunc('month', now()) + interval '1 month'
GROUP BY s.id, s.surname;

## 2. Every visit for HMS-000142

SELECT v.*
FROM visits v
JOIN patients p ON p.id = v.patient_id
WHERE p.mrn = 'HMS-000142'
ORDER BY v.visit_at DESC;

## 3. How much Mr Bello still owes

SELECT i.invoice_number,
       i.total_amount - COALESCE(SUM(pay.amount), 0) AS balance
FROM invoices i
JOIN visits v ON v.id = i.visit_id
JOIN patients p ON p.id = v.patient_id
LEFT JOIN payments pay ON pay.invoice_id = i.id
WHERE p.mrn = '<Bello's MRN>'
GROUP BY i.id, i.invoice_number, i.total_amount;

## 4. Which of today's appointments haven't arrived yet?

SELECT *
FROM appointments
WHERE status = 'booked'
  AND scheduled_at >= date_trunc('day', now())
  AND scheduled_at < date_trunc('day', now()) + interval '1 day';

## 5. Which appointments were no-shows last week?

SELECT *
FROM appointments
WHERE status = 'no-show'
  AND scheduled_at >= date_trunc('week', now()) - interval '1 week'
  AND scheduled_at < date_trunc('week', now());

## 6. How much money was collected this month?

SELECT COALESCE(SUM(amount), 0) AS collected
FROM payments
WHERE paid_at >= date_trunc('month', now())
  AND paid_at < date_trunc('month', now()) + interval '1 month';