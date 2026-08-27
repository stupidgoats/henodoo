# Project Task Checklist (Odoo 18)

Adds checklists to `project.task`, with each checklist's "done" state
automatically resetting whenever a task is copied — most importantly,
when the recurrence engine creates the next occurrence of a recurring
task.

## What's included

- **`project.task.checklist`** — one record per checklist on a task.
  Fields: `task_id`, `name`, `sequence`, `template_id` (which template it
  was created from, if any — informational only), `line_ids` (its
  items), and computed `total_count` / `done_count` / `progress` /
  `progress_label` (`"2/5"`-style text). Has its own
  `action_reset_checklist()` for a per-checklist "Reset Checklist"
  button.
- **`project.task.checklist.line`** — one record per checklist item.
  Fields: `checklist_id` (its parent checklist), `task_id` (a
  read-only related convenience field), `sequence`, `name`, `is_done`,
  `done_by` / `done_date` (auto-stamped when an item is checked). No
  per-item assignee or due date — the task's own `user_ids` and
  `date_deadline` cover that.
- **`project.task`** extension — `checklist_ids` (One2many to
  `project.task.checklist`), computed task-wide
  `checklist_total_count` / `checklist_done_count` / `checklist_progress`
  (aggregated across all of the task's checklists), and an
  `action_reset_checklist()` method wired to a "Reset All Checklists"
  button.
- A **Checklist** tab on the task form: an overall progress bar and
  done/total count for the task, an "Add Checklist from Template" button
  (always visible, even with no checklists yet), a "Reset All
  Checklists" button, and a plain list of the task's checklists (name,
  done/total, progress bar) — click a row to open that checklist, or use
  "Add a checklist" to create a new one ad hoc, no template required.
- Each **checklist's own form**: its name, its progress bar and
  done/total count, a "Reset Checklist" button, and its editable,
  drag-to-reorder list of items.
- A small **progress indicator on the kanban card** (icon + "n/total" +
  thin progress bar), aggregated across all of a task's checklists, only
  shown when the task has at least one checklist item.
- **Access rights** for `project.group_project_user` and
  `project.group_project_manager` (full CRUD on checklists, checklist
  lines, and applying templates; template *definitions* are read-only
  for regular users and full CRUD for managers, so managers curate the
  template library and everyone can use it). Portal access is
  intentionally not included — add rows to
  `security/ir.model.access.csv` if portal users should see/edit
  checklists on their tasks.
- **`project.checklist.template`** / **`project.checklist.template.line`**
  — a reusable checklist definition, independent of any task. Managed
  under **Project ▸ Configuration ▸ Checklist Templates**.
- **`project.checklist.template.apply`** — the wizard behind the task's
  "Add Checklist from Template" button. Picking a template creates a new
  checklist on the task (named after the template) with one item per
  template line, then opens that new checklist. The task's copy is then
  completely independent — editing it, or checking items off, never
  touches the template or any other task that applied it.

## How the recurrence reset works

Odoo's recurrence engine
(`project.task.recurrence._create_next_occurrence`, in
`addons/project/models/project_task_recurrence.py`) creates the next
occurrence by calling the standard `copy()` on `project.task`. One2many
fields are duplicated by the ORM's default `copy_data()` cascade —
task → checklists → items — so a task's checklists and their items
already carry over with no extra code required.

The only thing this module adds is an override of `copy_data()` on
`project.task.checklist.line` that forces `is_done`, `done_by`, and
`done_date` back to their empty state on every copy. That one override
covers all three duplication paths uniformly:

1. the recurrence engine creating the next occurrence,
2. a user clicking "Duplicate" on a task,
3. a project being duplicated (which cascades to its tasks).

No changes were made to `project.task.recurrence` or to Odoo's core
copy/duplicate logic — the reset is entirely local to this module's own
model.

## Design notes / things you may want to adjust

- **Why checklists are their own records, not a flat list with section
  markers**: an earlier version of this module kept a single flat
  `checklist_line_ids` list directly on the task, with a
  `display_type='line_section'` flag on some rows faking section
  headers. Visually that worked, but each section's "done/total" count
  then depended on its *sibling* rows within someone else's list — and
  Odoo's client-side onchange only reliably re-triggers a compute for
  the record actually being edited, not for sibling records whose
  compute merely depends on it. Two attempts to patch that (an explicit
  refresh call from the item's onchange) did not fix it in testing.
  Making each checklist a real parent record (`project.task.checklist`)
  with items as true `line_ids` children turns "this checklist's count"
  into a plain parent-aggregates-its-own-children computation — the same
  pattern the task-level progress bar has always used successfully — so
  it now updates live the same way.
  The trade-off: checking off items now happens on the checklist's own
  page/dialog rather than inline in one big list on the task form. That
  was a deliberate choice, confirmed as the preferred direction, in
  exchange for the counts actually being reliable.
- **Templates are a one-time copy, not a live link**: applying a
  template creates an independent checklist with no ongoing reference
  back to the template beyond the informational `template_id` field.
  Editing the template later does not affect checklists that already
  applied it, and editing a task's checklist never touches the template.
  If you want a "resync this checklist from its template" action later,
  that's an easy follow-up.
- **Reset scope**: currently *any* copy of a task resets all of its
  checklists, including a plain manual "Duplicate". If you want
  recurrence-only reset (i.e. manual duplicates keep their checked
  state), the fix is small: check
  `self.env.context.get('copy_project')` — the context flag the
  recurrence engine happens to set on `sudo().copy()` — inside
  `copy_data()` and only reset when that key is present, or more
  robustly, pass a dedicated context key from a
  `project.task.recurrence` override before calling `copy()`.
- **Blocking stage changes until every checklist is complete** was
  considered but left out of this version — let me know if you want it
  added (it would be a `write()` override on `project.task` checking
  `checklist_progress` when `stage_id` changes to a "folded"/done-type
  stage).

## Upgrade note (breaking change in v2.0.0)

v18.0.2.0.0 restructures checklists: items now belong to a
`project.task.checklist` record instead of directly to the task. The
`checklist_line_ids` field on `project.task` is gone, replaced by
`checklist_ids` (checklists) → `line_ids` (items). This is a schema
change — the `project.task.checklist.line` table's parent column is now
a required `checklist_id` instead of `task_id`. If you installed an
earlier 18.0.1.x version and have existing checklist items in a test
database, delete them (or drop/reinstall the module fresh) before
upgrading, since the new required column has nothing to populate itself
from on existing rows. No formal migration script is included, since
this has only been used in dev/test so far — say the word if you need
one for real data.

## Changelog

- **v18.0.2.0.0**: Restructured checklists so each one is its own
  `project.task.checklist` record with items as true one2many children,
  replacing the flat-list-with-section-markers design. This is what
  finally fixes per-checklist done/total counts not updating live (see
  the design note above) — it's a schema-level fix, not another CSS/
  onchange patch. Multiple checklists per task and ad-hoc/template
  creation both still work; checking off items now happens on each
  checklist's own page instead of inline in one shared list. Section-row
  CSS (`static/src/css/checklist.css`) is removed — it's no longer
  needed now that checklists are separate records with their own
  standard form.
- **v1.3.1**: Fixed `section_progress` only updating on save instead of
  live as items are checked — attempted via an explicit onchange
  refresh. Confirmed by the user not to actually fix it; superseded by
  the v2.0.0 restructuring above.
- **v1.3.0**: Four refinements based on visual testing feedback (the
  shading/border/color from v1.2.2 was confirmed working): stronger
  section contrast, items indented under their section, a
  `section_progress` "done/total" count on section rows, and a more
  visible checkbox border.
- **v1.2.2**: Fixed section-row CSS bugs found via testing:
  `background-color`/`border` were set on `<tr>` (browsers only render
  those on `<td>`), and the text color used `color: inherit` (which
  re-copies the parent's already-purple color instead of resetting it,
  fixed with an explicit `var(--bs-body-color)`).
- **v1.2.1**: Fixed section-row CSS not applying at all — it was scoped
  under a class set on the `<list>` tag, which doesn't get forwarded to
  any DOM ancestor when embedded in a one2many field on a form. Rewrote
  it unscoped, qualified by `:has(td[name="is_done"])` instead.
- **v1.2.0**: Fixed "Add Checklist from Template" being invisible on a
  task with no checklist items yet. Replaced reliance on
  `decoration-primary` alone for section styling with bundled CSS.
- **v1.1.0**: Added multiple checklists per task (as named sections in
  the same list, at the time) and reusable checklist templates.
- **v1.0.3**: Fixed section headers not rendering bold —
  `decoration-bold` is not a real Odoo attribute; the correct name is
  `decoration-bf`.
- **v1.0.2**: Removed the per-item assignee and due date fields — the
  task itself already carries these.
- **v1.0.1**: Fixed a `ParseError` on install — Odoo 18 renamed the
  `<tree>` view tag to `<list>`, including for nested one2many subviews
  inside a form.

## Verification performed in this environment

I don't have a running Odoo 18 + PostgreSQL instance in this sandbox, so
I could not do a live module install here. What I did verify:

- All `.py` files compile (`python -m py_compile`).
- `__manifest__.py` parses as a valid Python dict with the expected keys.
- All `.xml` files under `views/` and `wizard/` are well-formed XML.
- The view inheritance anchors (`project.view_task_form2`'s
  `description_page` page, and `project.view_task_kanban`'s
  `t-name="card"` / `footer`) were checked against the Odoo 18 source on
  GitHub at the time of writing, and had already been exercised
  successfully by earlier installs of this module before this
  restructuring — only the Checklist tab's inner content changed.

**Please still install this on a test database before production use**,
and read the Upgrade note above first if you have existing checklist
test data from an earlier version. If an xpath fails to match, Odoo's
error message will name the exact missing anchor, which is usually a
one-line fix — paste the traceback and I'll adjust it.

## Manual test checklist

1. Install (fresh, or per the Upgrade note if updating from 18.0.1.x)
   with `-i project_task_checklist` / `-u project_task_checklist` on a
   test database with the `project` app installed.
2. Open a task with **no** checklists yet and confirm **Add Checklist
   from Template** is visible on the empty Checklist tab.
3. Click **Add a checklist**, name it, add a few items, save. Confirm it
   now appears as a row in the Checklist tab's list with a done/total
   count and progress bar.
4. Click into that checklist and check an item off. Confirm its
   done/total count and progress bar update **immediately**, without
   saving — this is the behavior the whole restructuring was for.
5. Go back to the task's Checklist tab and confirm the row's own
   done/total/progress also reflects the change, and the task-level
   progress bar/count at the top of the tab and on the kanban card do
   too.
6. Go to **Project ▸ Configuration ▸ Checklist Templates**, create a
   template with a name and a few items.
7. Back on the task, click **Add Checklist from Template**, pick that
   template, confirm it creates a new checklist pre-filled with the
   template's items and opens it. Add a second checklist (from a
   template or ad hoc) and confirm the task now has multiple
   independent checklists, each with its own progress.
8. Edit the template's items afterward and confirm the task's
   already-added checklist is unaffected (it's a one-time copy).
9. As a non-manager project user, confirm you can apply a template to a
   task but cannot edit the template list itself (read-only); as a
   manager, confirm you can create/edit/delete templates.
10. Enable recurrence on the task (repeat e.g. daily), mark it done so
    the next occurrence is generated (or trigger the recurrence cron
    manually). Open the new occurrence and confirm **every** checklist
    on the task, and every item in each, is present but unchecked.
11. Click **Duplicate** on a task with partially-checked checklists and
    confirm the copy's checklists are all unchecked.
12. Click **Reset Checklist** on one checklist and confirm only its
    items uncheck; click **Reset All Checklists** on the task and
    confirm every checklist's items uncheck, without creating a new
    task either time.
