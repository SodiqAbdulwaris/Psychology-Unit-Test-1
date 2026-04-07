# Pending Changes Not Done Yet

This file is a planning note for changes that have not been fully implemented yet.

It is based on:

- `Backend_Requirements_v3_Revised.docx`
- the current backend code in this workspace
- the current project scope you stated:
  - staff and students migrations
  - students CSV import
  - staff APIs
  - appointment conflict detection and crisis logic
  - probably plugging real auth in test
  - Google two-way sync and related integrations later

This file is intentionally descriptive only.

- It does not mean the items below are already built.
- It does not change code.
- It is meant to be the reference we can use later when you want me to implement them.

## Current Important Reality

Some student work has already been adapted toward your preferred behavior, but the revised requirement document still expects a stricter inheritance pattern in a few places.

Examples:

- The requirements say `student.user_id = student.student_id`
- The current codebase still keeps an internal UUID in `users.id`
- The current codebase now uses `student_id` as the main public-facing identifier for students

That means some pending items below are really “alignment work” between the current implementation and the formal requirement document.

## 1. Psychologist Must Be a User + Staff Member

Status:

- Partially implied in the current code
- Not fully modeled and documented end-to-end yet

What the requirement says:

- All psychologists are users
- All psychologists are also staff members
- Staff details live in the `staff` table

What still needs to be clarified and/or implemented later:

- Exact psychologist creation flow:
  - create user first
  - then create staff record linked to that user
- Whether psychologists are created only by admin through `/users` first, then linked in `/staff`
- Whether `/staff` should be allowed to create both the base `users` row and the `staff` row in one action
- Clear rule for how `users.role`, `staff.staff_type`, and “psychologist” relate
- How admin privileges should be assigned to staff members in a controlled way

Recommended target behavior later:

- A psychologist should always have:
  - one `users` row
  - one `staff` row
  - `users.role = 'psychologist'`
  - `staff.staff_type = 'psychologist'`

Important correction to the earlier assumption:

- Staff are not always admins
- Admin access should be treated as a separate privilege assignment decision
- A staff member may later be marked as admin manually in the database
- Or we may later build an explicit admin-assignment function/endpoint for authorized use

Recommended target behavior later:

- Regular staff should remain non-admin by default
- Admin should be an elevated privilege intentionally granted to selected staff
- That privilege should be easy to audit and hard to assign accidentally

## 2. Staff ID / User ID Alignment

Status:

- Not fully aligned to the requirement document

What the requirement says:

- `staff.user_id = staff.staff_id`
- staff should inherit from users
- staff IDs should behave as the main staff-side identity reference

Your clarified product rule:

- Staff should have a `staff_id` that functions similarly to how `student_id` works for students
- `staff_id` should be the main human-facing identifier for staff records
- It should not be treated as “all staff are admins”; it is just the staff identity key

Current likely gap:

- The current app still treats `users.id` as an internal UUID and `staff.staff_id` as a separate value

Decision still pending:

- Whether to fully follow the requirement and make `staff_id` map directly to the base user identity
- Or keep the current internal UUID approach and expose `staff_id` as the external/public identifier

Important note:

- This is a larger schema decision and should be handled deliberately because it affects:
  - staff APIs
  - appointment relationships
  - psychologist assignment
  - auth/user management

Recommended target behavior later:

- Keep a stable internal base user identity if needed
- Expose and use `staff_id` as the staff-facing identifier in APIs and workflows where appropriate
- Define clearly whether lookups like `/staff/{id}` should eventually use `staff_id` instead of the internal UUID

## 3. Student/User Identity Alignment with the Requirement Document

Status:

- Partially implemented in a custom way

What the requirement says:

- `student.user_id = student.student_id`
- users.id should match student identity for students

Current code behavior:

- student-facing routes use `student_id`
- a linked `users` row is auto-created
- but `users.id` is still an internal UUID, not the school-issued student ID

Possible later implementation choices:

- Full requirement alignment:
  - redesign how student identity is stored in `users.id`
- Keep current hybrid approach:
  - `student_id` remains the main public identifier
  - `users.id` stays internal

This needs a deliberate product/data-model decision before more auth/user features are added.

## 4. Proper Users APIs Are Not Built Yet

Status:

- Not implemented in this workspace

Missing user-related APIs from the requirement doc:

- `POST /users`
- `GET /users`
- `GET /users/{id}`
- `PATCH /users/{id}`
- `PATCH /users/{id}/password`

Why this matters to your current scope:

- Proper user creation affects how staff and psychologists should be created
- It also affects how student import should create or link base users cleanly

Additional product rule to support later:

- Students should be able to create passwords for their accounts/IDs
- That means the auth/user layer should support a student account activation or password-setup flow
- We will need to decide whether students:
  - receive a pre-created account from CSV import and then set their password later
  - or are invited/activated through a first-login setup flow

Likely future pieces:

- student account activation endpoint
- password setup endpoint
- rules for first-time login
- secure verification that the person setting the password owns that student identity

## 5. Real Authentication / JWT / Refresh Token Flow

Status:

- Not fully implemented yet

Current gap:

- auth in the current code is still effectively stubbed for testing

Missing pieces from the requirement doc:

- real JWT verification
- access token issuance
- refresh token rotation
- logout with revocation
- refresh token theft / reuse detection
- `refresh_tokens` table

This directly affects testing realism and role enforcement confidence.

## 6. Staff API Scope Is Not Fully Complete Yet

Status:

- Basic staff APIs exist
- requirement-level completeness is still pending

Likely missing or incomplete areas to revisit later:

- stronger validation around psychologist vs non-psychologist staff creation
- better linkage to base users records
- self-access vs admin-access rules
- clearer creation lifecycle for psychologist accounts
- consistency between `users.role` and `staff.staff_type`

## 7. Student Profile Response Is Not Yet Fully Requirement-Aligned

Status:

- Partially implemented

Requirement mentions:

- full student profile with session count
- crisis flag
- family contact count

Current likely missing part:

- family contact count is not implemented because family features are not built yet

## 8. Full Crisis Booking Behavior Is Not Fully Implemented Yet

Status:

- Partially implemented

Already present:

- crisis bookings bypass conflict detection
- crisis logs are created
- a notification stub exists

Still pending from the requirement doc:

- notify psychologist about the conflict in a more complete way
- flag the conflicting normal appointment with a warning
- support manual resolution workflow for the psychologist

Your clarified product rule:

- Students with a historical or active crisis background, indicated by `crisis_flag = true`, should always have higher booking priority than non-crisis students
- Even if they are not explicitly booking a crisis intervention session, their appointment should still be treated as higher priority than a normal non-crisis user
- This should especially matter when:
  - there is a scheduling conflict
  - only a limited slot remains
  - prioritization logic is needed between two competing appointments

This creates a second type of priority:

- explicit crisis booking priority
- background crisis-history priority via `crisis_flag = true`

Recommended target behavior later:

- A non-crisis student booking should not displace a student with `crisis_flag = true`
- A student with `crisis_flag = true` should be eligible for elevated handling even when `is_crisis = false`
- The scheduling/conflict logic should define how lower-priority bookings are:
  - blocked
  - warned
  - flagged for rescheduling
  - or manually reviewed

Pending design decision:

- whether `crisis_flag = true` should automatically allow overbooking
- or only grant priority during conflict comparison and manual resolution

This should be designed carefully before implementation because it changes booking fairness and conflict logic.

## 9. Sessions Module Is Not Built Yet

Status:

- Not implemented yet

Missing endpoints from the requirement doc:

- `POST /sessions`
- `GET /sessions/{appointment_id}`
- `PATCH /sessions/{id}`
- `POST /sessions/{id}/audio`

Why this matters:

- sessions are the bridge to transcription, summaries, AI insights, and progress reports

## 10. AI Processing Pipeline Is Not Built Yet

Status:

- Not implemented yet

Missing requirement items:

- `ai_processing_jobs` workflow
- transcription
- AI summary generation
- AI insights generation
- retry logic
- timeout handling
- approval/edit workflow by psychologist

## 11. Progress Reports Are Not Built Yet

Status:

- Not implemented yet

Missing requirement items:

- `progress_reports` table workflow
- report generation logic
- psychologist-edited reports
- PDF export
- report period filtering
- 50-session cap behavior

## 12. Family / Consent Features Are Not Built Yet

Status:

- Not implemented yet

Missing requirement items:

- `family_contacts`
- `consent_records`
- family engagement APIs
- report sharing flows
- family communication permissions

## 13. Notifications Are Not Fully Built Yet

Status:

- Not implemented beyond a stub path

Missing requirement items:

- `notifications` table
- delivery state tracking
- email notifications through SendGrid
- crisis alert persistence
- booking confirmation notifications
- family invitation notifications

## 14. Google Calendar Two-Way Sync Is Not Built Yet

Status:

- Not implemented yet

Missing requirement items:

- Google OAuth setup
- appointment-to-calendar sync
- calendar-to-app sync
- conflict reconciliation
- persistent calendar event tracking

## 15. Audio Upload / Private Storage Controls Are Not Built Yet

Status:

- Not implemented yet

Missing requirement items:

- Supabase Storage private bucket flow
- signed URL access
- psychologist-only access control
- audio access audit logging

## 16. Audit Logging Is Not Built Yet

Status:

- Not implemented yet

Missing requirement items:

- `audit_logs` table
- logging of sensitive actions like:
  - view session
  - update student
  - delete appointment
  - export report
  - access audio

## 17. Caching Is Only Partially Present

Status:

- Partial

Current likely state:

- psychologist list cache is present
- student profile caching from the requirement doc is not yet fully implemented

Pending:

- student profile cache with invalidation on update
- broader cache review for requirement alignment

## 18. Idempotency Is Not Fully Requirement-Aligned Yet

Status:

- Partially implemented

Current behavior:

- in-memory idempotency exists

Requirement still expects:

- persistent idempotency storage
- `idempotency_keys` table
- expiry handling (24 hours)

## 19. Rate Limiting and Hard Security Controls Are Not Built Yet

Status:

- Not implemented yet

Missing requirement items:

- login rate limiting
- secure cookie-based refresh flow
- forced HTTPS behavior
- stricter CORS restriction
- structured security event logging

## 20. Migrations Need to Be Formalized

Status:

- Partially done manually during debugging

Current concern:

- several schema updates were applied directly to make the project work

Requirement still expects:

- Alembic-managed migrations
- version-controlled migration history
- no manual schema drift

This is especially important for:

- student identity changes
- staff identity changes
- unique indexes
- any future psychologist/user restructuring

## 21. Testing and Documentation Gaps Still Remaining

Status:

- Not complete yet

Requirement still expects:

- Postman collection for all APIs
- unit tests for services
- integration tests for APIs
- stronger coverage before later phases

## Suggested Implementation Order Later

When you want to continue, the safest order is:

1. Decide the final identity model for students and staff
2. Implement real users/auth flows
3. Align psychologist creation with users + staff relationship
4. Formalize schema history with migrations
5. Finish staff/student API alignment
6. Expand appointment crisis workflow
7. Build sessions
8. Add storage/AI/reporting
9. Add notifications, family, calendar sync

## My Working Understanding of Your Scope

If we stay focused on your current ownership, the highest-priority pending items are probably:

- psychologist as a properly modeled user + staff member
- staff are not automatically admins; admin assignment should be explicit and controllable
- staff ID / user ID relationship decision
- staff migration cleanup
- student migration cleanup
- keeping student CSV import aligned with the final identity model
- student password/account creation flow
- tightening appointment conflict and crisis logic
- crisis-history priority behavior using `crisis_flag`
- replacing auth stubs with real testable auth

Later/non-immediate items:

- Google Calendar two-way sync
- AI pipeline
- family flows
- report generation
- private audio handling
- full notification delivery
