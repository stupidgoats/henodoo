{
    'name': 'Project Task Checklist',
    'version': '18.0.3.2.0',
    'category': 'Services/Project',
    'summary': 'Add checklists to project tasks, checkable from the kanban card, auto-reset on recurrence',
    'description': """
Project Task Checklist
=======================

Adds checklists to project tasks.

Features
--------
* A task can carry any number of checklists, shown on the Checklist tab
  as a set of collapsible groups - click a checklist's header to expand
  it and work through its items in place, similar to an expandable
  "group by" list. Each checklist's resolved/total count and progress
  bar update live as you go, and so does the task-wide total.
* For a task that already has at least one checklist, the checklist
  moves to the very top of the task form - right under the task name -
  ahead of Project/Assignees/Deadline/etc. and the other tabs, since at
  that point it's usually the thing you actually opened the task to
  look at. A task with no checklist yet looks exactly as before, with a
  "Checklist" tab (first in the notebook) to add the first one; once
  that's saved, the widget "moves" itself to the top on the next form
  load.
* Each item has three states, not just checked/unchecked: Pending,
  Complete, or Not Needed (for items that turn out not to apply to this
  task). Click an item's own status icon (empty box / green check / red
  X) to toggle Complete; a separate small button next to the reorder/
  delete icons toggles Not Needed independently - no cycling through
  states to get to the one you want. Both Complete and Not Needed count
  as "resolved" for progress bars; the Checklist tab and the kanban card
  each break the count down by state so it's clear at a glance how many
  were actually done versus skipped.
* Kanban cards show a done/not-needed/pending badge row plus the actual
  checklist items underneath. Clicking an item's row cycles it Pending ->
  Complete -> Not Needed -> Pending, so any state is reachable with at
  most two clicks right on the card, no need to open the task. A
  separate "cancel" button sits at the far end of each row - well apart
  from the checkbox, to avoid accidental misclicks - as a one-click
  shortcut straight to Not Needed, for a chore that turns out not to
  apply without cycling through Complete first.
* Checklists can be created ad hoc, directly on a task, with no setup
  required.
* Reusable checklist templates (Project > Configuration > Checklist
  Templates), defined independently of any task. Applying one (via the
  "From template" picker on the Checklist tab) creates a new checklist
  on the task pre-filled with the template's items - the task's copy is
  then independent, so editing it never touches the template or other
  tasks.
* A combined progress bar and done/total count for the whole task, shown
  on the task form's Checklist section and on the kanban card.
* Checklist items automatically reset to Pending whenever a task is
  copied - this covers:

  - the recurrence engine creating the next occurrence of a recurring task
  - a user manually clicking "Duplicate" on a task
  - a project being duplicated (which duplicates its tasks)

  The reasoning: a checklist represents work still to be done on *this*
  instance of the task, so a freshly created copy should not inherit a
  previous instance's completed state.
* `project.task.action_reset_checklist()` / `project.task.checklist.
  action_reset_checklist()` remain available for setting items back to
  Pending without duplicating the task (e.g. from a server action) -
  there's just no button wired to them in this version, since resetting
  everything at once didn't turn out to have a real use case.

Architecture note
------------------
Each checklist (`project.task.checklist`) is a real record with its
items (`project.task.checklist.line`) as true one2many children, rather
than a flat list of items on the task with a flag marking some rows as
section headers. This matters for one concrete reason: Odoo's
client-side onchange machinery reliably recomputes a field that depends
on a record's own direct children (e.g. a checklist's resolved/total
count depending on `line_ids.state`) live, in the UI, without a save -
but it does not reliably propagate a computed change on one record to a
*sibling* record's displayed fields within the same list. Making each
checklist its own parent record turns "this section's count" into a
plain parent-aggregates-its-own-children computation, so it updates the
same way the task-level progress bar always has.

Technical note
--------------
Odoo's recurrence engine (`project.task.recurrence._create_next_occurrence`)
creates the next task occurrence via the standard `copy()` on
`project.task`. One2many fields are copied by the ORM's default
`copy_data` cascade (task -> checklists -> items), so no changes to the
recurrence engine itself are required - only
`project.task.checklist.line.copy_data()` is overridden to force
`state` back to 'pending' on every copy.

UI note
-------
The Checklist tab/top-of-form section is a small custom widget
(`checklist_accordion`), and the kanban card's checkable list is a
second, simpler widget (`checklist_kanban`) - neither is a standard
Odoo list. Both talk to the ORM directly and re-fetch their own data
after a change, rather than relying on the record's in-memory one2many
state. That is deliberate: it keeps every displayed count provably
correct without depending on how far Odoo's client-side onchange
propagates through nested one2many levels while a form stays unsaved,
or on kanban cards constantly re-rendering as the board scrolls or
regroups. One consequence: a brand-new, not-yet-saved task has nowhere
to attach a checklist to yet, so save the task once before adding its
first checklist.

Upgrade notes
-------------
Version 18.0.2.0.0 restructured checklist items to belong to a checklist
record instead of directly to the task. This was a breaking schema
change: the `checklist_line_ids` field is gone, replaced by
`checklist_ids` -> `line_ids`. Version 18.0.2.1.0 (the accordion UI) was
purely additive on top of that.

Version 18.0.2.2.0 replaced the item's `is_done` Boolean with a
three-way `state` Selection.

Version 18.0.2.3.0 only changed the Checklist tab's controls (separate
Complete/Not Needed buttons instead of one cycling icon; removed the
"Reset All Checklists" button) - no model or schema changes.

Version 18.0.3.0.0 adds the kanban card checklist (view + checkbox
widget) and moves the checklist to the top of the task form when the
task has one - no schema changes, purely new views/widgets on top of
the existing `project.task.checklist` / `.line` models.

Version 18.0.3.1.0 changes the kanban card's interaction: the row click
now cycles through all three states instead of only toggling Pending/
Complete, and adds a dedicated "cancel" (Not Needed) button at the far
end of each row, positioned well apart from the checkbox to avoid
accidental misclicks. Also increases the kanban checklist's text size
at desktop widths (768px+), where cards have more room to spare.

Version 18.0.3.1.1 fixes a bug (present since the accordion widget's
original version) where renaming a checklist or a checklist item never
actually saved: the name input is bound two-way via t-model, which
already syncs the in-memory value on every keystroke, so the onChange
handler's "did this actually change" guard was comparing the new value
against itself and always skipping the write. Renaming now always
writes (unless the new name is empty, which reloads instead of trying
to save a blank required field). This widget was always meant to save
each edit immediately over the ORM - no schema changes; no form Save
button appears (or needs to) for checklist edits by design.

Version 18.0.3.2.0 raises the kanban checklist's base (phone-width)
text size again - the 18.0.3.1.0 bump only applied at desktop widths
(768px+) and left phones at the original small size, which was still
too small to read comfortably. Font-size rules are now !important, to
make sure they win out over Odoo's own mobile kanban CSS regardless of
asset load order.
""",
    'author': 'Your Company',
    'website': '',
    'license': 'LGPL-3',
    'depends': ['project'],
    'data': [
        'security/ir.model.access.csv',
        'views/project_task_checklist_views.xml',
        'views/project_checklist_template_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'project_task_checklist/static/src/js/checklist_accordion_field.js',
            'project_task_checklist/static/src/js/checklist_kanban_field.js',
            'project_task_checklist/static/src/xml/checklist_accordion_field.xml',
            'project_task_checklist/static/src/xml/checklist_kanban_field.xml',
            'project_task_checklist/static/src/css/checklist_accordion.css',
            'project_task_checklist/static/src/css/checklist_kanban.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
