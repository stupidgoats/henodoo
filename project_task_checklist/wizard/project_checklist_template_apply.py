# -*- coding: utf-8 -*-
from odoo import fields, models


class ProjectChecklistTemplateApply(models.TransientModel):
    """Server-side logic behind the "From template" picker on a task's
    Checklist tab. Creates a new project.task.checklist on the task, named
    after the template, with one item line per template line.

    This model has no view of its own - the Checklist tab's JS widget
    (checklist_accordion_field.js) creates a record of this wizard and
    calls action_apply() on it directly via the ORM, then re-fetches the
    task's checklists itself. No dialog is opened and no navigation
    happens; the return value below is unused by that caller and is only
    there in case something else ever invokes this the traditional way
    (button + window action)."""
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
