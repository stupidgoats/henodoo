# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ProjectTask(models.Model):
    _inherit = 'project.task'

    checklist_line_ids = fields.One2many(
        'project.task.checklist.line', 'task_id', string='Checklist',
        copy=True)

    checklist_total_count = fields.Integer(
        string='Checklist Items', compute='_compute_checklist_progress')
    checklist_done_count = fields.Integer(
        string='Checklist Items Done', compute='_compute_checklist_progress')
    checklist_progress = fields.Float(
        string='Checklist Progress', compute='_compute_checklist_progress',
        help='Percentage of checklist items marked as done. Section '
             'headers are not counted as items.')

    @api.depends('checklist_line_ids.is_done', 'checklist_line_ids.display_type')
    def _compute_checklist_progress(self):
        for task in self:
            lines = task.checklist_line_ids.filtered(lambda l: not l.display_type)
            total = len(lines)
            done = len(lines.filtered('is_done'))
            task.checklist_total_count = total
            task.checklist_done_count = done
            task.checklist_progress = (done / total * 100.0) if total else 0.0

    def action_reset_checklist(self):
        """Manually uncheck every checklist item on this task, without
        duplicating the task. Complements the automatic reset that happens
        when a task is copied (see ProjectTaskChecklistLine.copy_data)."""
        self.checklist_line_ids.filtered(lambda l: not l.display_type).write({
            'is_done': False,
        })
