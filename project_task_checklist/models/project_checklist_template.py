# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ProjectChecklistTemplate(models.Model):
    """A reusable checklist definition, independent of any task. Applied to
    a task via the 'Add Checklist from Template' wizard (see
    project.checklist.template.apply), which copies its items onto the
    task as a new section in project.task.checklist_line_ids."""
    _name = 'project.checklist.template'
    _description = 'Checklist Template'
    _order = 'name'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    line_ids = fields.One2many(
        'project.checklist.template.line', 'template_id',
        string='Items', copy=True)
    item_count = fields.Integer(compute='_compute_item_count')

    @api.depends('line_ids')
    def _compute_item_count(self):
        for template in self:
            template.item_count = len(template.line_ids)


class ProjectChecklistTemplateLine(models.Model):
    _name = 'project.checklist.template.line'
    _description = 'Checklist Template Item'
    _order = 'sequence, id'

    template_id = fields.Many2one(
        'project.checklist.template', string='Template',
        required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(default=10)
    name = fields.Char(required=True)
