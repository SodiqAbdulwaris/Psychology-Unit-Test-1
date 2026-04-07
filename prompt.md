# Codex Prompt — Students, Staff & Appointments Module
### PsyUnit Backend | Python FastAPI | Member 2

---

## Context

You are building the **Students, Staff, and Appointments** module for PsyUnit — a crisis-aware psychology booking system for a university. The backend uses **Python 3.11+ with FastAPI**, async SQLAlchemy 2.0 (asyncpg driver), PostgreSQL via Supabase, and Pydantic v2 for schema validation.

The full app already has the following in place (do NOT regenerate these):
- `app/core/config.py` — Pydantic BaseSettings for env vars
- `app/core/database.py` — async SQLAlchemy engine and `get_db` session dependency
- `app/core/security.py` — JWT verification and `get_current_user` dependency that returns `{"id": UUID, "role": str}`
- `app/utils/response.py` — standard response envelope:

```python
def success(message: str, data=None): 
    return {"success": True, "message": message, "data": data}

def error(message: str): 
    return {"success": False, "message": message, "data": None}
```

- `app/utils/pagination.py` — pagination helper that returns `{"data": [...], "pagination": {"total": int, "limit": int, "offset": int, "has_next": bool}}`

All responses MUST use these utilities. All list endpoints MUST use pagination.

---

## Database Tables (already migrated — do NOT re-create)

```sql
-- users (base table — owned by Member 1, do not modify)
users(id UUID PK, email, password_hash, full_name, phone, date_of_birth, 
      gender, role ENUM('admin','psychologist','staff','student'), 
      is_active BOOLEAN DEFAULT TRUE, deleted_at TIMESTAMPTZ, 
      created_at, updated_at)

-- students
students(user_id UUID PK FK→users.id CASCADE, student_id VARCHAR(50) UNIQUE NOT NULL,
         class_level VARCHAR(50), assigned_psychologist_id UUID FK→staff.user_id NULLABLE,
         guidance_counselor VARCHAR(255), emergency_contact VARCHAR(255),
         emergency_phone VARCHAR(30), crisis_flag BOOLEAN DEFAULT FALSE,
         created_at TIMESTAMPTZ DEFAULT now(), updated_at TIMESTAMPTZ)

-- staff
staff(user_id UUID PK FK→users.id CASCADE, staff_id VARCHAR(50) UNIQUE NOT NULL,
      staff_type ENUM('psychologist','counselor','administrator','support_staff') NOT NULL,
      department VARCHAR(100), hire_date DATE, specialization TEXT,
      max_appointments_per_day INTEGER DEFAULT 8,
      created_at TIMESTAMPTZ DEFAULT now(), updated_at TIMESTAMPTZ)

-- appointments
appointments(id UUID PK, student_id UUID FK→students.user_id NOT NULL,
             psychologist_id UUID FK→staff.user_id NOT NULL,
             start_time TIMESTAMPTZ NOT NULL, end_time TIMESTAMPTZ NOT NULL,
             status ENUM('booked','completed','cancelled','no_show'),
             is_crisis BOOLEAN DEFAULT FALSE, crisis_note TEXT,
             booking_source ENUM('student_portal','psychologist_manual','walk_in'),
             calendar_event_id VARCHAR, deleted_at TIMESTAMPTZ,
             created_at TIMESTAMPTZ DEFAULT now())

-- crisis_logs
crisis_logs(id UUID PK, appointment_id UUID FK→appointments.id,
            student_id UUID FK→students.user_id,
            severity_level ENUM('low','medium','high'),
            action_taken TEXT, alert_sent_at TIMESTAMPTZ,
            resolved BOOLEAN DEFAULT FALSE, resolved_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT now())
```

---

## SQLAlchemy ORM Models

Generate async-compatible SQLAlchemy 2.0 ORM models in `app/models/`:

- `students.py` — Student model
- `staff.py` — Staff model  
- `appointments.py` — Appointment model
- `crisis_logs.py` — CrisisLog model

Use `mapped_column()` and `Mapped[]` type annotations (SQLAlchemy 2.0 style). Use `sqlalchemy.dialects.postgresql.UUID` for UUID fields. Use Python `enum.Enum` classes for ENUM columns.

---

## Pydantic Schemas

Generate Pydantic v2 schemas in `app/schemas/`:

### `students.py`
- `StudentCreate` — fields: student_id, class_level, guidance_counselor, emergency_contact, emergency_phone (all optional except student_id)
- `StudentUpdate` — all optional: class_level, assigned_psychologist_id, crisis_flag, guidance_counselor, emergency_contact, emergency_phone
- `StudentResponse` — all student fields + full_name and email from joined users table + session_count (int) + crisis_flag

### `staff.py`
- `StaffCreate` — fields: user_id (UUID), staff_type, department, hire_date, specialization, max_appointments_per_day
- `StaffUpdate` — all optional: department, specialization, max_appointments_per_day
- `StaffResponse` — all staff fields + full_name and email from joined users table

### `appointments.py`
- `AppointmentCreate` — fields: student_id (UUID), psychologist_id (UUID), start_time (datetime), end_time (datetime), is_crisis (bool default False), crisis_note (optional), booking_source
- `AppointmentUpdate` — all optional: status, start_time, end_time, crisis_note
- `AppointmentResponse` — all appointment fields + student full_name + psychologist full_name + linked session summary if exists (optional)

---

## Services (Business Logic)

Generate service classes in `app/services/`:

### `app/services/student_service.py` — `StudentService` class

Methods:
- `async get_all(db, filters: dict, limit: int, offset: int)` — list with filters: class_level, crisis_flag, assigned_psychologist_id. Return paginated.
- `async get_by_id(db, student_id: UUID)` — return full profile. Raise 404 if not found or soft-deleted.
- `async update(db, student_id: UUID, data: StudentUpdate)` — patch allowed fields. Set updated_at.
- `async soft_delete(db, student_id: UUID)` — set users.deleted_at = now(). Admin only.
- `async get_sessions(db, student_id: UUID, limit, offset)` — return all sessions for student ordered by date desc.
- `async get_crisis_logs(db, student_id: UUID)` — return all crisis_logs for student.
- `async bulk_import_csv(db, file_contents: bytes)` — parse CSV, validate rows, insert valid students, return `{"inserted": N, "skipped": N, "errors": [{row, reason}]}`.
  - Required columns: student_id, first_name, last_name
  - Optional: date_of_birth (validate YYYY-MM-DD), gender, class_level, email (validate format), emergency_contact, emergency_phone
  - Max: 5 MB / 2,000 rows
  - Check for duplicate student_id within the CSV itself
  - Check for duplicate student_id against the database
  - For valid rows: create a user record (role='student') + student record in one transaction

### `app/services/staff_service.py` — `StaffService` class

Methods:
- `async create(db, data: StaffCreate)` — link to existing users record. Raise 404 if user not found. Raise 409 if staff record already exists.
- `async get_all(db, filters: dict, limit, offset)` — filter by staff_type, department. Paginated.
- `async get_psychologists(db)` — return all active psychologists (staff_type='psychologist', is_active=True). Cache for 10 minutes using functools.lru_cache equivalent.
- `async get_by_id(db, staff_id: UUID)` — raise 404 if not found.
- `async update(db, staff_id: UUID, data: StaffUpdate)` — patch allowed fields.
- `async soft_delete(db, staff_id: UUID)` — set users.deleted_at = now().

### `app/services/appointment_service.py` — `AppointmentService` class

Methods:
- `async create(db, data: AppointmentCreate, background_tasks: BackgroundTasks)` — full booking logic:
  1. Check psychologist exists and is active
  2. Run conflict detection query (see below) — UNLESS is_crisis=True
  3. If is_crisis=True: allow booking even if conflict exists, create crisis_logs entry, add background task to send notification stub
  4. If conflict exists for normal booking: raise 409 with message "Psychologist has a conflicting booking at this time"
  5. Create appointment record
  6. Return appointment with 201 status
- `async get_all(db, filters: dict, limit, offset)` — filter by: psychologist_id, student_id, status, is_crisis, date_range (start/end). Paginated.
- `async get_availability(db, psychologist_id: UUID, date: date)` — return list of free 1-hour slots for the given date based on booked appointments and max_appointments_per_day.
- `async get_by_id(db, appointment_id: UUID)` — return appointment with linked session summary if it exists.
- `async update(db, appointment_id: UUID, data: AppointmentUpdate)` — if time is changed, re-run conflict detection. Set updated_at.
- `async soft_delete(db, appointment_id: UUID)` — only allowed if status is 'booked' or 'cancelled' AND no linked session exists. Raise 422 otherwise.

**Conflict Detection Query (use this exact logic):**

```python
# Use tstzrange overlap for conflict detection
conflict = await db.execute(
    select(Appointment).where(
        Appointment.psychologist_id == psychologist_id,
        Appointment.status == 'booked',
        Appointment.deleted_at.is_(None),
        Appointment.id != exclude_id,  # exclude self on update
        func.tstzrange(Appointment.start_time, Appointment.end_time).op('&&')(
            func.tstzrange(start_time, end_time)
        )
    ).limit(1)
)
```

---

## Routers

Generate FastAPI routers in `app/routers/`:

### `app/routers/students.py`

```
POST   /students/upload-csv        → Admin or Psychologist only
GET    /students                   → Admin or Psychologist only — query params: class_level, crisis_flag, assigned_psychologist_id, limit=20, offset=0
GET    /students/{id}              → Admin or Psychologist only
PATCH  /students/{id}              → Admin or Psychologist only
DELETE /students/{id}              → Admin only
GET    /students/{id}/sessions     → Admin or Psychologist only — paginated, ordered by date desc
GET    /students/{id}/crisis-logs  → Admin or Psychologist only
```

### `app/routers/staff.py`

```
POST   /staff                      → Admin only
GET    /staff                      → Admin only — query params: staff_type, department, limit=20, offset=0
GET    /psychologists              → Admin or Staff — no pagination, cached 10 min
GET    /staff/{id}                 → Admin or Self
PATCH  /staff/{id}                 → Admin or Self
DELETE /staff/{id}                 → Admin only
```

### `app/routers/appointments.py`

```
POST   /appointments                                    → Psychologist or Admin
GET    /appointments                                    → Psychologist or Admin — filters: psychologist_id, student_id, status, is_crisis, start_date, end_date, limit=20, offset=0
GET    /appointments/availability/{psychologist_id}     → All authenticated — query param: date (YYYY-MM-DD)
GET    /appointments/{id}                               → Psychologist or Admin
PATCH  /appointments/{id}                               → Psychologist or Admin
DELETE /appointments/{id}                               → Admin only
```

---

## RBAC Enforcement

Use FastAPI `Depends` for role checking. Import `get_current_user` from `app/core/security`. Example pattern:

```python
def require_roles(*roles: str):
    def dependency(current_user: dict = Depends(get_current_user)):
        if current_user["role"] not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return Depends(dependency)

# Usage in router
@router.get("/students")
async def list_students(current_user=require_roles("admin", "psychologist"), ...):
    ...
```

Psychologists may only access students assigned to them (`assigned_psychologist_id == current_user["id"]`). Enforce this in service methods when role is 'psychologist'.

---

## Idempotency

All POST, PATCH, DELETE routes must accept an `Idempotency-Key` header. Check this header and if a key has been seen before, return the cached response. For Week 1, use an in-memory dict as the store (replace with DB table later):

```python
idempotency_store: dict = {}  # key → response dict
```

---

## CSV Import Endpoint Detail

`POST /students/upload-csv` accepts `multipart/form-data` with a `file` field (CSV). Use `python-multipart`. Stream the file and validate:

- File size ≤ 5 MB
- Max 2,000 data rows (excluding header)
- Required columns present: student_id, first_name, last_name
- Return immediately with `{"inserted": N, "skipped": N, "errors": [{row: int, reason: str}]}`

---

## Notification Stub

When a crisis appointment is created, call this stub as a background task (do NOT block the response):

```python
# app/utils/notification_stub.py
async def send_crisis_alert(psychologist_id: str, student_id: str, appointment_id: str):
    # Stub — Member 1 will replace this with real SendGrid logic
    print(f"[CRISIS ALERT] Psychologist {psychologist_id} notified for student {student_id}, appointment {appointment_id}")
```

---

## File Structure to Generate

```
app/
├── models/
│   ├── students.py
│   ├── staff.py
│   ├── appointments.py
│   └── crisis_logs.py
├── schemas/
│   ├── students.py
│   ├── staff.py
│   └── appointments.py
├── services/
│   ├── student_service.py
│   ├── staff_service.py
│   └── appointment_service.py
├── routers/
│   ├── students.py
│   ├── staff.py
│   └── appointments.py
└── utils/
    └── notification_stub.py
```

---

## Hard Rules

- All route handlers must be `async def`
- All DB calls must use `await` with the async session
- Never use `time.sleep()` — use `asyncio.sleep()` if needed
- Never construct raw SQL with f-strings — always use SQLAlchemy ORM or `text()` with bound parameters
- Never return passwords, token hashes, or session content in any response
- Soft-deleted records (`deleted_at IS NOT NULL`) must be excluded from all list and GET queries
- All responses must use `success()` or `error()` from `app/utils/response.py`
- All list endpoints must use the pagination utility
- All ENUM values must exactly match the schema definitions above
