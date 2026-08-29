# -*- coding: utf-8 -*-
"""This version replaces project.task.checklist.line's is_done Boolean
with a three-way state Selection (pending / done / not_needed), so items
can be marked "not needed" as well as complete.

By the time a post-migrate script runs, Odoo has already added the new
`state` column (defaulting every existing row to 'pending') but has NOT
dropped the old `is_done` column - Odoo never auto-drops columns for
fields removed from a model. So the old data is still sitting right
there; this just carries it over once, then leaves the orphaned column
alone (harmless, and dropping it isn't this script's job).

Safe to run more than once and safe on a database that never had this
module: it checks the old column exists before touching anything.
"""


def migrate(cr, version):
    cr.execute("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'project_task_checklist_line'
          AND column_name = 'is_done'
    """)
    if not cr.fetchone():
        return

    cr.execute("""
        UPDATE project_task_checklist_line
           SET state = 'done'
         WHERE is_done IS TRUE
    """)

    # done_by/done_date were renamed to resolved_by/resolved_date - carry
    # over the timestamp/user of items that were already checked, if
    # those old columns are still present too.
    cr.execute("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'project_task_checklist_line'
          AND column_name = 'done_by'
    """)
    if cr.fetchone():
        cr.execute("""
            UPDATE project_task_checklist_line
               SET resolved_by = done_by,
                   resolved_date = done_date
             WHERE is_done IS TRUE
        """)
