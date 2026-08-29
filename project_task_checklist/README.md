# Project Task Checklist (Odoo 18)

Adds checklists to `project.task`, with each item automatically resetting
to Pending whenever a task is copied — most importantly, when the
recurrence engine creates the next occurrence of a recurring task.

## What's included

- **`project.task.checklist`** — one record per checklist on a task.
  Fields: `task_id`, `name`, `sequence`, `template_id` (which template it
  was created from, if any — informational only), `line_ids` (its
  items), and computed `total_count` / `done_count` / `not_needed_count`
  / `pending_count` / `progress` / `progress_label` (`"2/5"`-style text,
  resolved-out-of-total). Has its own `action_reset_checklist()` for a
  per-checklist "Reset Checklist" button.
- **`project.task.checklist.line`** — one record per checklist item.
  Fields: `checklist_id` (its parent checklist), `task_id` (a
  read-only related convenience field), `sequence`, `name`, `state`
  (Pending / Complete / Not Needed), `resolved_by` / `resolved_date`
  (auto-stamped when an item is marked Complete or Not Needed, cleared
  if it's set back to Pending). No per-item assignee or due date — the
  task's own `user_ids` and `date_deadline` cover that.
- **`project.task`** extension — `checklist_ids` (One2many to
  `project.task.checklist`), computed task-wide
  `checklist_total_count` / `checklist_done_count` /
  `checklist_not_needed_count` / `checklist_pending_count` /
  `checklist_progress` (aggregated across all of the task's checklists;
  `checklist_progress` counts both Complete and Not Needed as resolved),
  and an `action_reset_checklist()` method wired to a "Reset All
  Checklists" button.
- A **Checklist** tab on the task form, rendered by a small custom widget
  (`checklist_accordion`, under `static/src/js/`): an overall progress
  bar and a complete/not-needed/pending breakdown for the whole task, a
  "Reset All Checklists" button, and each checklist shown as a
  collapsible group — click its header to expand it and work through its
  items in place, similar to an expandable "group by" list. Each item
  has a status icon (empty square / green check / grey dash) that cycles
  Pending → Complete → Not Needed → Pending on click, plus a text label
  spelling out its current state. Each group's own resolved/total count
  and progress bar update live as you go, and so does the task-wide
  total at the top. "Add a checklist" creates one ad hoc, no template
  required; a "From template" dropdown next to it applies a saved
  template.
- A **generic form view** for `project.task.checklist` still exists
  (`view_task_checklist_form`) as the model's default form for
  technical/backend access, but the task's Checklist tab no longer
  navigates to it — everything happens inline in the accordion.
- A small **progress breakdown on the kanban card**: a green check icon
  with the Complete count, a grey dash icon with the Not Needed count,
  an empty-square icon with the Pending count (each only shown when
  non-zero), plus a thin progress bar — aggregated across all of a
  task's checklists, only shown when the task has at least one checklist
  item.
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
- **`project.checklist.template.apply`** — the server-side logic behind
  the Checklist tab's "From template" dropdown. Picking a template
  creates a new checklist on the task (named after the template) with
  one item per template line. It has no view/dialog of its own anymore
  — the accordion widget creates a wizard record and calls its
  `action_apply()` directly via the ORM, then re-fetches the task's
  checklists itself. The task's copy is then completely independent —
  editing it, or checking items off, never touches the template or any
  other task that applied it.

## How the recurrence reset works

Odoo's recurrence engine
(`project.task.recurrence._create_next_occurrence`, in
`addons/project/models/project_task_recurrence.py`) creates the next
occurrence by calling the standard `copy()` on `project.task`. One2many
fields are duplicated by the ORM's default `copy_data()` cascade —
task → checklists → items — so a task's checklists and their items
already carry over with no extra code required.

The only thing this module adds is an override of `copy_data()` on
`project.task.checklist.line` that forces `state` back to `'pending'`
(and clears `resolved_by`/`resolved_date`) on every copy. That one
override covers all three duplication paths uniformly:

1. the recurrence engine creating the next occurrence,
2. a user clicking "Duplicate" on a task,
3. a project being duplicated (which cascades to its tasks).

No changes were made to `project.task.recurrence` or to Odoo's core
copy/duplicate logic — the reset is entirely local to this module's own
model.

## Design notes / things you may want to adjust

- **Why the Checklist tab is a custom widget instead of a standard
  one2many list**: making each checklist its own record (see below)
  fixed live updates *when you edit a checklist in isolation on its own
  page*. Going back to editing everything inline, on the task's own
  form, in one accordion — which is what "expand like group by" asks
  for — reintroduces the exact question that restructuring was meant to
  settle: does a change three levels down (task → checklist → item)
  reliably propagate back up through Odoo's client-side onchange while
  the form is still unsaved? The honest answer is "probably, since
  `@api.depends('checklist_ids.line_ids.is_done')` is a real dependency
  path, not the sibling-lookup hack the old design used" — but "probably"
  is exactly the kind of thing that turned out wrong twice already in
  this module's history. So the accordion widget sidesteps the question
  entirely: every action (check an item, rename, add, delete, reorder,
  apply a template, reset all) writes straight to the ORM and then
  re-reads the task's checklists from the server, rather than trusting
  in-memory onchange propagation. It's a network round trip per click
  instead of an instant client-side recompute, but every number shown is
  guaranteed correct rather than "probably fine."
  One real trade-off from this: a brand-new, not-yet-saved task has no
  id yet, so there's nowhere to attach a checklist to — save the task
  once first, the same constraint the old "Add Checklist from Template"
  button already had (it also needed an existing task id).
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
  It's still this model split that makes the accordion widget's numbers
  trustworthy — it's just that the widget gets there by asking the
  server after every change instead of leaning on client-side computes
  at all (see the note above).
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

## Upgrade notes

v18.0.2.0.0 restructured checklists: items now belong to a
`project.task.checklist` record instead of directly to the task. The
`checklist_line_ids` field on `project.task` is gone, replaced by
`checklist_ids` (checklists) → `line_ids` (items). This was a schema
change — the `project.task.checklist.line` table's parent column is now
a required `checklist_id` instead of `task_id`. If you installed a
version earlier than that and have existing checklist items in a test
database, delete them (or drop/reinstall the module fresh) before
upgrading, since the required column has nothing to populate itself from
on existing rows. No migration script covers this one, since it predates
this module having any real usage worth preserving.

v18.0.2.1.0 (the accordion UI) only changed how the Checklist tab
renders — no model or field changes, so no data concerns upgrading from
18.0.2.0.0.

v18.0.2.2.0 (Pending/Complete/Not Needed) replaced `is_done` with
`state` — see the changelog entry below. Unlike the v2.0.0 change, this
one *does* ship a migration script
(`migrations/18.0.2.2.0/post-migrate.py`) that automatically carries any
already-checked items over to `state = 'done'` when you run `-u`, so no
manual cleanup is needed.

## Changelog

- **v18.0.2.2.0**: Replaced the item's `is_done` Boolean with a
  three-way `state` (Pending / Complete / Not Needed), so an item can be
  marked as not applicable instead of forced into checked-or-unchecked.
  `done_by`/`done_date` were renamed `resolved_by`/`resolved_date` and
  now stamp on either resolved state. Checklist and task progress
  (`progress`/`checklist_progress`) count Complete and Not Needed as
  resolved; new `not_needed_count`/`checklist_not_needed_count` and
  `pending_count`/`checklist_pending_count` fields track each state on
  its own. In the accordion, an item's status icon cycles through the
  three states on click. The kanban card badge now shows three counts
  (complete/not needed/pending) instead of one "done" count. This is a
  schema change — see the Upgrade notes below — but ships a migration
  script that carries existing checked items over automatically, so no
  manual cleanup is needed this time.
- **v18.0.2.1.0**: Replaced the plain "click a checklist to open it"
  list on the Checklist tab with an accordion — each checklist is a
  collapsible group you expand to check off its items in place, similar
  to an expandable "group by" list (requested after testing the click-
  through version). Implemented as a small custom widget
  (`checklist_accordion`) that talks to the ORM directly and re-fetches
  after every change, rather than relying on the standard one2many list
  renderer or in-memory onchange propagation — see the design note above
  for why. The "Add Checklist from Template" button moved from the
  toolbar into a "From template" dropdown inside the widget, since the
  widget now owns all checklist actions itself; its wizard dialog/view
  is gone but the underlying wizard model is unchanged. Also added
  simple up/down reordering (no drag-and-drop) for both checklists and
  items. No model or schema changes.
- **v18.0.2.0.0**: Restructured checklists so each one is its own
  `project.task.checklist` record with items as true one2many children,
  replacing the flat-list-with-section-markers design. This is what
  finally fixes per-checklist done/total counts not updating live (see
  the design note above) — it's a schema-level fix, not another CSS/
  onchange patch. Multiple checklists per task and ad-hoc/template
  creation both still work. Section-row CSS
  (`static/src/css/checklist.css`) is removed — it's no longer needed
  now that checklists are separate records.
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
  successfully by earlier installs of this module — the Checklist tab's
  inner content is now just a single custom-widget field, so this
  anchor risk hasn't changed.
- The `checklist_accordion` widget's JS was checked with `node --check`
  for syntax errors, and its owl/web-client API calls (`useService`,
  `standardFieldProps`, the field registry shape, `record.resId`,
  `record.load()`) were written to match documented Odoo 17/18 patterns.
  I don't have a live Odoo web client here to actually render it, though
  — a custom field widget is the one part of this module I can't fully
  verify without your browser's console. If the Checklist tab shows a
  blank area or a "component crashed" box instead of the accordion,
  open the browser console (F12), copy the error, and send it over —
  that'll usually point straight at the fix.

**Please still install this on a test database before production use**,
and read the Upgrade notes above first if you have existing checklist
test data from an earlier version. If an xpath fails to match, Odoo's
error message will name the exact missing anchor, which is usually a
one-line fix — paste the traceback and I'll adjust it.

## Manual test checklist

1. Install/upgrade with `-i project_task_checklist` /
   `-u project_task_checklist` on a test database with the `project` app
   installed. If you had checked items from before v18.0.2.2.0, check
   the database for a couple of them afterward and confirm they came
   through as **Complete** (the post-migrate script's job).
2. Open a task and go to the **Checklist** tab. On a task with no
   checklists yet, confirm it shows "No checklists yet" plus the
   "Add a checklist" input and "From template" dropdown — no JS errors
   in the browser console.
3. Type a name in **New checklist name…**, press Enter (or click **Add a
   checklist**). Confirm it appears immediately as a collapsed group with
   "0/0 resolved".
4. Click the group's header to expand it, add a couple of items via
   **Add an item…**. Confirm each appears indented underneath as
   **Pending** with an empty-square icon, and the group's "n/total"
   count and progress bar update immediately after each add.
5. Click an item's status icon once. Confirm it becomes **Complete**
   (green check, strikethrough text) and the group's resolved/total
   count and progress bar update **immediately** — no Save needed.
   Click it again and confirm it becomes **Not Needed** (grey dash,
   strikethrough); click once more and confirm it's back to
   **Pending** (normal text). This 3-way cycle, and the fact that both
   Complete and Not Needed move the progress bar, is the main thing
   this round of changes was for.
6. With a mix of states across a couple of items, confirm the overall
   summary at the top of the tab shows separate complete/not-needed/
   pending counts that add up correctly, and the kanban card for this
   task (from the Tasks list/kanban view) shows the same three counts.
7. Collapse the group (click its header again) and confirm it collapses
   without losing anything; re-expand and confirm each item kept its
   state.
8. Rename a checklist (edit the name field in its header, click away) and
   rename an item the same way; confirm both persist after a page
   refresh.
9. Use the ▲/▼ icons on a checklist's header to reorder it relative to
   another checklist, and the ▲/▼ icons on an item to reorder it within
   its checklist; confirm the new order survives a page refresh.
10. Go to **Project ▸ Configuration ▸ Checklist Templates**, create a
    template with a name and a few items.
11. Back on the task's Checklist tab, pick that template from the
    **From template…** dropdown. Confirm it adds a new, expanded group
    pre-filled with the template's items, all Pending.
12. Edit the template's items afterward and confirm the task's
    already-added checklist is unaffected (it's a one-time copy).
13. As a non-manager project user, confirm you can apply a template from
    the dropdown but cannot edit the template list itself (read-only);
    as a manager, confirm you can create/edit/delete templates.
14. Click the trash icon on one checklist item, then on a whole
    checklist group; confirm each disappears immediately and doesn't
    come back on refresh.
15. Enable recurrence on the task (repeat e.g. daily), mark it done so
    the next occurrence is generated (or trigger the recurrence cron
    manually). Open the new occurrence and confirm **every** checklist
    on the task, and every item in each, is present and back to
    **Pending** — including any that were Not Needed on the original.
16. Click **Duplicate** on a task with a mix of Complete/Not Needed/
    Pending items and confirm the copy's checklists are all reset to
    Pending.
17. Click **Reset All Checklists** at the top of the tab on a task with
    some Complete/Not Needed items and confirm every item goes back to
    Pending, without creating a new task.
18. Create a brand-new task (don't save yet) and open its Checklist tab
    — confirm it shows the "save the task first" message rather than
    erroring. Save the task, reopen the tab, and confirm it now lets you
    add a checklist.
