# Changes So Far

## Should You Enable RLS in Supabase?

Short answer: yes, but with the right setup.

- If your frontend will ever talk directly to Supabase tables, enable Row Level Security (RLS).
- If all database access goes only through your FastAPI backend using a trusted server connection, RLS is less urgent, but still a good safety layer.
- Do not enable RLS without also creating policies, or your app may suddenly lose access to tables.

Recommended approach:

- Keep backend server access on the backend only.
- Enable RLS for app-facing tables in Supabase.
- Add explicit policies for the roles/users that should be able to read or write data.

## Problems Found and How They Were Solved

### 1. Wrong route path used during testing

Problem:

- The route was tested as `/students/upload_csv`.
- The actual route defined in the code is `/students/upload-csv`.

Impact:

- Requests to the underscore route failed.

Fix:

- Confirmed the router definition and tested the correct path: `POST /students/upload-csv`.

Files involved:

- `app/routers/students.py`

### 2. ORM foreign key setup was broken

Problem:

- The `Student` ORM model referenced `users.id` with a foreign key.
- The `users` table was defined on a separate `MetaData()` object from the ORM models.

Impact:

- SQLAlchemy could not resolve the foreign key mapping.
- The upload route failed before it could query or insert data.

Observed error:

- `NoReferencedTableError`

Fix:

- Changed `app/models/tables.py` to use `Base.metadata` instead of a separate `MetaData()` instance.

Files changed:

- `app/models/tables.py`

### 3. Models were not guaranteed to load before DB usage

Problem:

- Some models and tables were not imported centrally at startup.

Impact:

- SQLAlchemy mapper configuration could fail or miss relationships during app execution.

Fix:

- Added model imports in `app/models/__init__.py`.
- Imported `app.models` from `app/core/database.py` so model registration happens before DB work.

Files changed:

- `app/models/__init__.py`
- `app/core/database.py`

### 4. Supabase database tables did not exist

Problem:

- The project expected `users`, `students`, `staff`, `appointments`, `crisis_logs`, and `sessions` tables.
- The connected Supabase database did not contain those tables yet.

Impact:

- Uploads failed with missing-table database errors.

Observed error:

- `relation "students" does not exist`

Fix:

- Created the missing tables from the project SQLAlchemy metadata.

Result:

- The database now has the required tables for this module.

### 5. Email validation rejected every CSV row

Problem:

- CSV import used Pydantic `EmailStr` validation.
- The environment did not have the `email-validator` package installed.

Impact:

- Every row with a valid email was still rejected as invalid.

Observed error:

- `ImportError: email-validator is not installed`

Fix:

- Replaced the strict dependency-based email validation with a lightweight standard-library validation check.

Files changed:

- `app/services/student_service.py`

### 6. HTTP upload returned 500 before retesting stabilized

Problem:

- Early HTTP tests failed because the route was still hitting the unresolved ORM and schema issues above.

Impact:

- The endpoint returned `500 Internal Server Error`.

Fix:

- Fixed metadata/model loading.
- Created missing tables.
- Fixed email validation.
- Retested the route after the underlying issues were resolved.

## Final Status

Current working endpoint:

- `POST /students/upload-csv`

Confirmed behavior:

- First valid import inserted 10 students successfully.
- Re-uploading the same CSV returns success with rows skipped as duplicates.

## Main Lessons

- In SQLAlchemy, all related ORM tables should share the same metadata.
- Import order matters when relationships depend on other models.
- A route can be correct while the real failure is deeper in ORM or database setup.
- Validation code should not depend on packages that are not installed unless they are explicitly included in project requirements.
- Database schema assumptions should be verified early when debugging API failures.

## Additional Changes Made After Initial Fix

### 7. Student ID became the main student identifier

Problem:

- Student routes and relationships were still relying on the internal UUID-style `user_id`.
- You wanted student records to be identified by `student_id` instead.

Impact:

- Student lookups were tied to an internal key that should not be the main public-facing identifier.

Fix:

- Updated the Python models so `students.student_id` is the student primary key.
- Updated student services and routes to use `student_id` for retrieval, update, delete, session lookup, and crisis-log lookup.
- Updated related tables so `appointments.student_id` and `crisis_logs.student_id` reference `students.student_id`.
- Migrated the live Supabase schema to match the code changes.

Files changed:

- `app/models/students.py`
- `app/models/appointments.py`
- `app/models/crisis_logs.py`
- `app/services/student_service.py`
- `app/services/appointment_service.py`
- `app/routers/students.py`
- `app/routers/appointments.py`

### 8. Added student search by student ID

Problem:

- There was no dedicated student-ID search flow for users who want to search by student ID instead of internal identifiers.

Fix:

- Added a search function in the student service.
- Added a dedicated endpoint: `GET /students/search?q=<student_id>`
- Added `student_id` as a filter option on `GET /students`
- Search supports exact match and partial match on `student_id`

Files changed:

- `app/services/student_service.py`
- `app/routers/students.py`

### 9. Added stronger duplicate protection

Problem:

- Duplicate records should be blocked for:
  - `users.email`
  - `students.student_id`
  - `students.user_id`

Fix:

- Added application-level duplicate checks during CSV import for:
  - duplicate student IDs in the CSV
  - duplicate emails in the CSV
  - existing student IDs already in the database
  - existing emails already in the database
- Added database-level uniqueness protection:
  - unique email rule on users
  - unique index on `students.user_id`
  - unique index on `students.student_id`

Files changed:

- `app/models/tables.py`
- `app/services/student_service.py`

### 10. Made automatic user creation from student imports explicit

Answer:

- Yes, student users were already being auto-generated during CSV import.

Where it happens:

- A new internal UUID is created for the `users` table row.
- Then a matching `students` row is created for that same person.

Improvement made:

- Refactored the user-creation logic into a dedicated helper method so it is clearer that importing a student automatically creates a linked user account row.

Files changed:

- `app/services/student_service.py`
