# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ProjectTaskChecklistLine(models.Model):
    _name = 'project.task.checklist.line'
    _description = 'Task Checklist Item'
    _order = 'sequence, id'

    checklist_id = fields.Many2one(
        'project.task.checklist', string='Checklist',
        required=True, ondelete='cascade', index=True)
    task_id = fields.Many2one(
        related='checklist_id.task_id', string='Task',
        store=True, index=True, readonly=True)
    company_id = fields.Many2one(
        related='checklist_id.company_id', store=True, index=True,
        readonly=True)

    sequence = fields.Integer(default=10)
    name = fields.Char(required=True)

    is_done = fields.Boolean(string='Done')
    done_by = fields.Many2one(
        'res.users', string='Done by', readonly=True, copy=False)
    done_date = fields.Datetime(
        string='Done on', readonly=True, copy=False)

    @api.onchange('is_done')
    def _onchange_is_done(self):
        for line in self:
            if line.is_done:
                line.done_by = self.env.user
                line.done_date = fields.Datetime.now()
            else:
                line.done_by = False
                line.done_date = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._sync_done_stamp(vals)
        return super().create(vals_list)

    def write(self, vals):
        if 'is_done' in vals:
            self._sync_done_stamp(vals)
        return super().write(vals)

    def _sync_done_stamp(self, vals):
        """Keep done_by/done_date consistent even when is_done is set
        programmatically (import, API call, ...) rather than through the
        onchange above."""
        if vals.get('is_done'):
            vals.setdefault('done_by', self.env.user.id)
            vals.setdefault('done_date', fields.Datetime.now())
        elif 'is_done' in vals and not vals.get('is_done'):
            vals.setdefault('done_by', False)
            vals.setdefault('done_date', False)

    def copy_data(self, default=None):
        # Any duplication of a checklist line - whether triggered by a
        # manual "Duplicate" of the task, a project duplication, or (most
        # importantly) the recurrence engine creating the next occurrence
        # of a recurring task - should start unchecked: the work has not
        # actually been redone yet on the new copy.
        default = dict(default or {})
        default.setdefault('is_done', False)
        default.setdefault('done_by', False)
        default.setdefault('done_date', False)
        return super().copy_data(default=default)
