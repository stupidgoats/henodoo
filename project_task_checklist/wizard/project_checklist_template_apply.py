# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ProjectChecklistTemplateApply(models.TransientModel):
    """Wizard behind the task's 'Add Checklist from Template' button.
    Copies a project.checklist.template's items onto the task as a new
    section (a display_type='line_section' line, named after the
    template) followed by one item line per template line, appended to
    the end of the task's checklist_line_ids."""
    _name = 'project.checklist.template.apply'
    _description = 'Add Checklist From Template'

    task_id = fields.Many2one(
        'project.task', required=True,
        default=lambda self: self.env.context.get('active_id'))
    template_id = fields.Many2one(
        'project.checklist.template', string='Checklist Template',
        required=True)

    def action_apply(self):
        self.ensure_one()
        line_model = self.env['project.task.checklist.line']
        existing_sequences = self.task_id.checklist_line_ids.mapped('sequence')
        next_sequence = (max(existing_sequences) + 10) if existing_sequences else 10

        line_model.create({
            'task_id': self.task_id.id,
            'display_type': 'line_section',
            'name': self.template_id.name,
            'sequence': next_sequence,
        })
        next_sequence += 10

        item_vals_list = []
        for template_line in self.template_id.line_ids.sorted('sequence'):
            item_vals_list.append({
                'task_id': self.task_id.id,
                'name': template_line.name,
                'sequence': next_sequence,
            })
            next_sequence += 10
        if item_vals_list:
            line_model.create(item_vals_list)

        return {'type': 'ir.actions.act_window_close'}
