{
    'name': 'Project Task Checklist',
    'version': '18.0.2.3.0',
    'category': 'Services/Project',
    'summary': 'Add checklists to project tasks, auto-reset on recurrence',
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
* Each item has three states, not just checked/unchecked: Pending,
  Complete, or Not Needed (for items that turn out not to apply to this
  task). Click an item's own status icon (empty box / green check / red
  X) to toggle Complete; a separate small button next to the reorder/
  delete icons toggles Not Needed independently - no cycling through
  states to get to the one you want. Both Complete and Not Needed count
  as "resolved" for progress bars; the Checklist tab and the kanban card
  each break the count down by state so it's clear at a glance how many
  were actually done versus skipped.
* Checklists can be created ad hoc, directly on a task, with no setup
  required.
* Reusable checklist templates (Project > Configuration > Checklist
  Templates), defined independently of any task. Applying one (via the
  "From template" picker on the Checklist tab) creates a new checklist
  on the task pre-filled with the template's items - the task's copy is
  then independent, so editing it never touches the template or other
  tasks.
* A combined progress bar and done/total count for the whole task, shown
  on the task form's Checklist tab and on the kanban card.
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
The Checklist tab is a small custom widget (`checklist_accordion`), not a
standard Odoo list - it talks to the ORM directly and re-fetches its own
data after every change (add/rename/delete/mark complete or not needed/
reorder/apply template), rather than relying on the record's in-memory
one2many state.
That is deliberate: it keeps every displayed count provably correct
without depending on how far Odoo's client-side onchange propagates
through nested one2many levels while the form is still unsaved. One
consequence: a brand-new, not-yet-saved task has nowhere to attach a
checklist to yet, so save the task once before adding its first
checklist.

Upgrade notes
-------------
Version 18.0.2.0.0 restructured checklist items to belong to a checklist
record instead of directly to the task (see Architecture note above).
This was a breaking schema change: the `checklist_line_ids` field is
gone, replaced by `checklist_ids` -> `line_ids`. If you have existing
checklist items from an install earlier than that, remove them (or
reinstall the module fresh) before upgrading, since the required
`checklist_id` column has no data to populate itself from on existing
rows. Version 18.0.2.1.0 (the accordion UI) was purely additive on top
of that - no schema changes.

Version 18.0.2.2.0 replaces the item's `is_done` Boolean with a
three-way `state` Selection (see Features above). This module ships a
migration script (`migrations/18.0.2.2.0/post-migrate.py`) that carries
existing checked items over to `state = 'done'` automatically on
upgrade, so no manual cleanup is needed for this one.

Version 18.0.2.3.0 only changes the Checklist tab's controls (separate
Complete/Not Needed buttons instead of one cycling icon; removed the
"Reset All Checklists" button) - no model or schema changes.
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
            'project_task_checklist/static/src/xml/checklist_accordion_field.xml',
            'project_task_checklist/static/src/css/checklist_accordion.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
