{
    'name': 'Project Task Checklist',
    'version': '18.0.2.0.0',
    'category': 'Services/Project',
    'summary': 'Add checklists to project tasks, auto-reset on recurrence',
    'description': """
Project Task Checklist
=======================

Adds checklists to project tasks.

Features
--------
* A task can carry any number of checklists, each with its own name and
  its own reorderable list of items. Click into a checklist to check off
  items - each checklist's done/total count and progress bar update live
  as you go.
* Checklists can be created ad hoc, directly on a task, with no setup
  required.
* Reusable checklist templates (Project > Configuration > Checklist
  Templates), defined independently of any task. Applying a template to
  a task (via "Add Checklist from Template") creates a new checklist on
  the task pre-filled with the template's items - the task's copy is
  then independent, so editing it never touches the template or other
  tasks.
* A combined progress bar and done/total count for the whole task, shown
  on the task form's Checklist tab and on the kanban card.
* Checklist items automatically reset to "unchecked" whenever a task is
  copied - this covers:

  - the recurrence engine creating the next occurrence of a recurring task
  - a user manually clicking "Duplicate" on a task
  - a project being duplicated (which duplicates its tasks)

  The reasoning: a checklist represents work still to be done on *this*
  instance of the task, so a freshly created copy should not inherit a
  previous instance's completed state.
* A manual "Reset All Checklists" button on the task, and a per-checklist
  "Reset Checklist" button, for cases where you want to re-run a
  checklist without duplicating the whole task.

Architecture note
------------------
Each checklist (`project.task.checklist`) is a real record with its
items (`project.task.checklist.line`) as true one2many children, rather
than a flat list of items on the task with a flag marking some rows as
section headers. This matters for one concrete reason: Odoo's
client-side onchange machinery reliably recomputes a field that depends
on a record's own direct children (e.g. a checklist's done/total count
depending on `line_ids.is_done`) live, in the UI, without a save - but it
does not reliably propagate a computed change on one record to a
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
`project.task.checklist.line.copy_data()` is overridden to force the
"done" state back to False on every copy.

Upgrade note
------------
Version 18.0.2.0.0 restructures checklist items to belong to a checklist
record instead of directly to the task (see Architecture note above).
This is a breaking schema change: the `checklist_line_ids` field is gone,
replaced by `checklist_ids` -> `line_ids`. If you have existing checklist
items from an earlier 18.0.1.x install, remove them (or reinstall the
module fresh) before upgrading, since the new required `checklist_id`
column has no data to populate itself from on existing rows.
""",
    'author': 'Your Company',
    'website': '',
    'license': 'LGPL-3',
    'depends': ['project'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/project_checklist_template_apply_views.xml',
        'views/project_task_checklist_views.xml',
        'views/project_checklist_template_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
