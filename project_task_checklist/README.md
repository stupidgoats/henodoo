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
  `project.group_project_manager` (full CRUD on checklist lines and on
  applying templates; template *definitions* are read-only for regular
  users and full CRUD for managers, so managers curate the template
  library and everyone can use it). Portal access is intentionally not
  included — add rows to `security/ir.model.access.csv` if portal users
  should see/edit checklists on their tasks.
- **`project.checklist.template`** / **`project.checklist.template.line`**
  — a reusable checklist definition, independent of any task. Managed
  under **Project ▸ Configuration ▸ Checklist Templates**.
- **`project.checklist.template.apply`** — the wizard behind the task's
  "Add Checklist from Template" button. Picking a template appends a new
  section (named after the template) plus one line per template item to
  that task's checklist. The task's copy is then completely independent
  — editing it, or checking items off, never touches the template or any
  other task that applied it.

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

- **Structure**: multiple checklists on one task are still a single
  flat `checklist_line_ids` list under the hood — each checklist is a
  `display_type='line_section'` header row. This was a deliberate choice
  over giving each checklist its own record/page: it reuses the exact
  list mechanics already proven to work (drag-reorder, inline add,
  recurrence reset), with one shared progress bar for the whole task
  rather than one per checklist. If you later decide you want a separate
  progress bar per checklist, that's a bigger structural change (a
  `project.task.checklist` header model with its own page) — ask and
  I'll scope it.
- **Section row styling** comes from a small bundled CSS file
  (`static/src/css/checklist.css`), not decoration attributes alone.
  `decoration-bf`/`decoration-primary` in the view still mark section
  rows semantically, but the CSS is what turns them into a shaded,
  bordered, uppercase heading row — `decoration-primary` alone renders
  as blue link-colored text with no background in Odoo's dark theme,
  which reads as a clickable link, not a heading.
  The CSS selectors target `tr.o_data_row.fw-bold` /
  `tr.o_data_row.text-primary` (the actual classes Odoo's list renderer
  puts on the row for those two decorations — confirmed via a live
  DevTools inspection, not a guess), each additionally qualified with
  `:has(td[name="is_done"])` so the rule only ever matches rows in a
  checklist list (the `is_done` field is specific to
  `project.task.checklist.line`) rather than some unrelated decorated
  list elsewhere in Odoo. It is deliberately **not** scoped under a
  wrapper class on the `<list>` tag — that was the original approach,
  but `class="..."` on a `<list>` embedded inside a one2many field on a
  form does not reliably get forwarded to any DOM ancestor, so a
  selector scoped that way silently matched nothing. If styling ever
  looks off again, open a checklist row in the browser inspector and
  check the classes actually on the `<tr>` — that's how the fix above
  was found.
- **Templates are a one-time copy, not a live link**: applying a
  template creates independent lines with no ongoing reference back to
  the template (beyond the section's name). Editing the template later
  does not affect tasks that already applied it, and editing a task's
  checklist never touches the template. If you want a "resync this
  section from its template" action later, that's an easy follow-up.
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

- **v1.2.2**: Fixed two more section-row CSS bugs found via testing:
  uppercase/bold text was showing (confirming the selectors *do* match),
  but the shaded background and top border weren't, and the text was
  still purple instead of neutral. Cause #1: `background-color`/`border`
  were set on the `<tr>` — browsers generally don't render background or
  border set directly on a table row, only on its `<td>` cells, so both
  rules were silently inert; moved them onto the cells. Cause #2: the
  text color rule used `color: inherit`, which just re-copies the
  parent's already-purple `text-primary` color rather than resetting it;
  changed to an explicit `var(--bs-body-color)` (Bootstrap 5's normal
  text-color variable) instead.
- **v1.2.1**: Fixed section-row CSS not applying at all. The selectors
  were scoped under `.o_checklist_line_list`, a class set on the `<list>`
  tag in the view — but that class doesn't get forwarded to any DOM
  ancestor when the list is embedded in a one2many field on a form, so
  every selector silently matched nothing (confirmed via a live DevTools
  inspection, which also confirmed `fw-bold`/`text-primary` *are* the
  right classes to target). Rewrote the CSS unscoped, qualified instead
  by `:has(td[name="is_done"])` so it still only touches checklist rows.
- **v1.2.0**:
  - Fixed the "Add Checklist from Template" button being invisible on a
    task with no checklist items yet — it was nested inside the same
    `invisible="not checklist_total_count"` block as the progress bar,
    so it never showed up until *something* already existed to make the
    progress bar meaningful. It's now a sibling, always visible; the
    progress bar, done count, and "Reset Checklist" stay hidden until
    there's something to show/reset.
  - Replaced reliance on `decoration-primary` alone for section styling
    with a bundled CSS file giving section rows a real shaded/bordered/
    uppercase heading treatment (see "Section row styling" above for
    why, and the fallback strategy).
- **v1.1.0**: Added multiple checklists per task (as named sections in
  the same list) and reusable checklist templates — a new
  `project.checklist.template` model managed under Project ▸
  Configuration ▸ Checklist Templates, plus an "Add Checklist from
  Template" button/wizard on the task that copies a template's items in
  as a new section. Ad-hoc sections (no template) still work exactly as
  before via "Add a section".
- **v1.0.3**: Fixed section headers not actually rendering bold. The
  view used `decoration-bold`, which is not a real Odoo attribute (it's
  silently ignored — no error, it just does nothing). The correct name
  is `decoration-bf`. Also added `decoration-primary` alongside it, so
  section rows now get bold text *and* a light background tint, using
  only built-in, documented Odoo list decorations (no custom CSS/JS).
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
2. Open a task with **no** checklist items yet and confirm **Add
   Checklist from Template** is visible on the empty Checklist tab (this
   was broken in v1.1.0).
3. Add a section and a couple of items, check one off. Confirm the
   section row is clearly shaded/bordered/uppercase (not just bold blue
   text), the progress bar and kanban badge update, and there is no
   assignee/due date column on checklist items.
4. Go to **Project ▸ Configuration ▸ Checklist Templates**, create a
   template with a name and a few items.
5. Back on the task, click **Add Checklist from Template**, pick that
   template, confirm it adds a new section with the template's items at
   the bottom of the existing checklist (not replacing it). Add a second
   checklist from the same or another template and confirm you now have
   multiple independent sections.
6. Edit the template's items afterward and confirm the task's
   already-added checklist is unaffected (it's a one-time copy).
7. As a non-manager project user, confirm you can apply a template to a
   task but cannot edit the template list itself (read-only); as a
   manager, confirm you can create/edit/delete templates.
8. Enable recurrence on the task (repeat e.g. daily), mark it done so
   the next occurrence is generated (or trigger the recurrence cron
   manually). Open the new occurrence and confirm **every** checklist
   item across **every** section is present but unchecked.
9. Click **Duplicate** on a task with a partially-checked checklist and
   confirm the copy's checklist is unchecked.
10. Click **Reset Checklist** on a task with checked items and confirm
    all items uncheck without creating a new task.
