# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ProjectTask(models.Model):
    _inherit = 'project.task'

    checklist_ids = fields.One2many(
        'project.task.checklist', 'task_id', string='Checklists',
        copy=True)

    checklist_total_count = fields.Integer(
        string='Checklist Items', compute='_compute_checklist_progress')
    checklist_done_count = fields.Integer(
        string='Checklist Items Done', compute='_compute_checklist_progress')
    checklist_progress = fields.Float(
        string='Checklist Progress', compute='_compute_checklist_progress',
        help="Percentage of checklist items marked as done, across all "
             "of this task's checklists.")

    @api.depends('checklist_ids.line_ids.is_done')
    def _compute_checklist_progress(self):
        for task in self:
            lines = task.checklist_ids.line_ids
            total = len(lines)
            done = len(lines.filtered('is_done'))
            task.checklist_total_count = total
            task.checklist_done_count = done
            task.checklist_progress = (done / total * 100.0) if total else 0.0

    def action_reset_checklist(self):
        """Uncheck every item across every checklist on this task, without
        duplicating the task. Complements the automatic reset that happens
        when a task is copied (see ProjectTaskChecklistLine.copy_data)."""
        self.checklist_ids.line_ids.write({'is_done': False})
