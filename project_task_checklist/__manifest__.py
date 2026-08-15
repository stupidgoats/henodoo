{
    'name': 'Project Task Checklist',
    'version': '18.0.1.0.0',
    'category': 'Services/Project',
    'summary': 'Add checklists to project tasks, auto-reset on recurrence',
    'description': """
Project Task Checklist
=======================

Adds a lightweight checklist to project tasks.

Features
--------
* Reorderable checklist items, with optional section headers to group
  long checklists.
* Optional per-item assignee and due date.
* Progress (done / total) shown on the task form and on the kanban card.
* Checklist state automatically resets to "unchecked" whenever a task is
  copied - this covers:

  - the recurrence engine creating the next occurrence of a recurring task
  - a user manually clicking "Duplicate" on a task
  - a project being duplicated (which duplicates its tasks)

  The reasoning: a checklist represents work still to be done on *this*
  instance of the task, so a freshly created copy should not inherit a
  previous instance's completed state.
* A manual "Reset Checklist" button on the task, for cases where you want
  to re-run a checklist without duplicating the whole task.

Technical note
--------------
Odoo's recurrence engine (`project.task.recurrence._create_next_occurrence`)
creates the next task occurrence via the standard `copy()` on
`project.task`. One2many fields are copied by the ORM's default
`copy_data` cascade, so no changes to the recurrence engine itself are
required - only `project.task.checklist.line.copy_data()` is overridden
to force the "done" state back to False on every copy.
""",
    'author': 'Your Company',
    'website': '',
    'license': 'LGPL-3',
    'depends': ['project'],
    'data': [
        'security/ir.model.access.csv',
        'security/project_task_checklist_security.xml',
        'views/project_task_checklist_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
