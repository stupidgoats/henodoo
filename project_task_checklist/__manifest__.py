{
    'name': 'Project Task Checklist',
    'version': '18.0.1.2.2',
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
* Multiple checklists per task: a task's checklist is one combined list
  where each checklist is its own shaded, uppercase section heading row
  - add as many sections as you like, ad hoc, with no setup required.
* Reusable checklist templates (Project > Configuration > Checklist
  Templates), defined independently of any task. Applying a template to
  a task adds a new section pre-filled with the template's items, via
  the "Add Checklist from Template" button - the task's copy is then
  independent, so editing it never touches the template or other tasks.

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
        'wizard/project_checklist_template_apply_views.xml',
        'views/project_task_checklist_views.xml',
        'views/project_checklist_template_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'project_task_checklist/static/src/css/checklist.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
