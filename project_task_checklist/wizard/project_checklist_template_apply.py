# -*- coding: utf-8 -*-
from odoo import fields, models


class ProjectChecklistTemplateApply(models.TransientModel):
    """Wizard behind the task's 'Add Checklist from Template' button.
    Creates a new project.task.checklist on the task, named after the
    template, with one item line per template line - then opens that new
    checklist's own page."""
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
        checklist = self.env['project.task.checklist'].create({
            'task_id': self.task_id.id,
            'name': self.template_id.name,
            'template_id': self.template_id.id,
        })
        if self.template_id.line_ids:
            self.env['project.task.checklist.line'].create([{
                'checklist_id': checklist.id,
                'name': template_line.name,
                'sequence': template_line.sequence,
            } for template_line in self.template_id.line_ids.sorted('sequence')])

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'project.task.checklist',
            'res_id': checklist.id,
            'view_mode': 'form',
            'target': 'current',
        }
