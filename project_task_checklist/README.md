# Project Task Checklist (Odoo 18)

Adds a lightweight, reorderable checklist to `project.task`, with the
checklist's "done" state automatically resetting whenever a task is
copied — most importantly, when the recurrence engine creates the next
occurrence of a recurring task.

## What's included

- **`project.task.checklist.line`** — one record per checklist row.
  Fields: `task_id`, `sequence`, `display_type` (blank = normal item,
  `line_section` = non-checkable section header), `name`, `is_done`,
  `done_by` / `done_date` (auto-stamped when an item is checked). No
  per-item assignee or due date — the task's own `user_ids` and
  `date_deadline` cover that.
- **`project.task`** extension — `checklist_line_ids` (One2many),
  computed `checklist_total_count` / `checklist_done_count` /
  `checklist_progress`, and an `action_reset_checklist()` method wired to
  a manual "Reset Checklist" button.
- A **Checklist** tab on the task form: progress bar, editable list with
  drag-to-reorder, inline "Add a checklist item" / "Add a section"
  controls.
- A small **progress indicator on the kanban card** (icon + "n/total" +
  thin progress bar), only shown when a task has checklist items.
- **Access rights** for `project.group_project_user` and
  `project.group_project_manager` (full CRUD). Portal access is
  intentionally not included — add a row to
  `security/ir.model.access.csv` if portal users should see/edit
  checklists on their tasks.

## How the recurrence reset works

Odoo's recurrence engine
(`project.task.recurrence._create_next_occurrence`, in
`addons/project/models/project_task_recurrence.py`) creates the next
occurrence by calling the standard `copy()` on `project.task`. One2many
fields are duplicated by the ORM's default `copy_data()` cascade, so the
checklist's *items* already carry over with no extra code required.

The only thing this module adds is an override of
`copy_data()` on `project.task.checklist.line` that forces `is_done`,
`done_by`, and `done_date` back to their empty state on every copy. That
one override covers all three duplication paths uniformly:

1. the recurrence engine creating the next occurrence,
2. a user clicking "Duplicate" on a task,
3. a project being duplicated (which cascades to its tasks).

No changes were made to `project.task.recurrence` or to Odoo's core
copy/duplicate logic — the reset is entirely local to this module's own
model.

## Design notes / things you may want to adjust

- **Structure**: this is the "flat checklist" model (one list of items
  directly on the task) rather than a reusable-template model. If you
  later want checklist templates that can be centrally edited and
  applied to future recurring occurrences, the line model already has
  the shape (`display_type`, `sequence`) to add an optional
  `template_line_id` without breaking anything — that would be a
  separate, additive module/change.
- **Reset scope**: currently *any* copy of a task resets its checklist,
  including a plain manual "Duplicate". If you want recurrence-only
  reset (i.e. manual duplicates keep their checked state), the fix is
  small: check `self.env.context.get('copy_project')` — which is the
  context flag the recurrence engine happens to set on `sudo().copy()`
  — inside `copy_data()` and only reset when that key is present, or
  more robustly, pass a dedicated context key from a
  `project.task.recurrence` override before calling `copy()`.
- **Blocking stage changes until the checklist is complete** was
  considered but left out of this first version — let me know if you
  want it added (it would be a `write()` override on `project.task`
  checking `checklist_progress` when `stage_id` changes to a "folded"/
  done-type stage).

## Changelog

- **v1.0.2**: Removed the per-item `user_id` (assignee) and
  `date_deadline` (due date) fields — the task itself already carries
  an assignee and a due date, so per-item versions were redundant.
- **v1.0.1**: Fixed a `ParseError` ("Field \"display_type\" does not
  exist in model \"project.task\"") on install. Odoo 18 renamed the
  `<tree>` view tag to `<list>` — including for nested one2many subviews
  inside a form, which is what the checklist tab uses. The subview
  under `checklist_line_ids` now uses `<list>` instead of `<tree>`; no
  other attributes changed.

## Verification performed in this environment

I don't have a running Odoo 18 + PostgreSQL instance in this sandbox, so
I could not do a live module install here. What I did verify:

- All `.py` files compile (`python -m py_compile`).
- `__manifest__.py` parses as a valid Python dict with the expected keys.
- `views/project_task_checklist_views.xml` is well-formed XML.
- The view inheritance anchors (`project.view_task_form2`'s
  `description_page` page, and `project.view_task_kanban`'s
  `t-name="card"` / `footer`) were checked against the Odoo 18 source on
  GitHub at the time of writing.

**Please still install this on a test database before production use.**
View inheritance is the most likely thing to need a small tweak if your
instance has customizations to the task form/kanban view, or if a point
release has shifted the base view slightly — if an xpath fails to match,
Odoo's error message will name the exact missing anchor, which is
usually a one-line fix.

In particular, the kanban card patch (`view_task_kanban_inherit_checklist`)
had not actually been exercised by a real install as of v1.0.1 — the form
view's `<tree>`/`<list>` bug above stopped installation before Odoo got to
it. If it errors on your instance, paste the traceback and I'll adjust
the xpath/card syntax to match your exact base view.

## Manual test checklist

1. Install the module (`-i project_task_checklist`) on a test database
   with the `project` app installed.
2. Open a task, go to the **Checklist** tab, add a section and a couple
   of items, check one off. Confirm the progress bar and kanban badge
   update. Confirm there is no assignee/due date column on checklist
   items.
3. Enable recurrence on the task (repeat e.g. daily), mark it done so
   the next occurrence is generated (or trigger the recurrence cron
   manually). Open the new occurrence and confirm the checklist items
   are present but **all unchecked**.
4. Click **Duplicate** on a task with a partially-checked checklist and
   confirm the copy's checklist is unchecked.
5. Click **Reset Checklist** on a task with checked items and confirm
   all items uncheck without creating a new task.
