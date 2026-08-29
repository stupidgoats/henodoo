# -*- coding: utf-8 -*-
from odoo import api, fields, models

RESOLVED_STATES = ('done', 'not_needed')


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

    state = fields.Selection(
        [('pending', 'Pending'),
         ('done', 'Complete'),
         ('not_needed', 'Not Needed')],
        string='Status', default='pending', required=True,
        help="Pending: not done yet. Complete: the work was done. Not "
             "Needed: turned out not to apply to this task - counted as "
             "resolved (it no longer needs anyone's attention) but kept "
             "separate from Complete so it's clear at a glance which "
             "items were actually done versus skipped.")
    resolved_by = fields.Many2one(
        'res.users', string='Resolved by', readonly=True, copy=False,
        help="Who last marked this item Complete or Not Needed.")
    resolved_date = fields.Datetime(
        string='Resolved on', readonly=True, copy=False)

    @api.onchange('state')
    def _onchange_state(self):
        for line in self:
            if line.state in RESOLVED_STATES:
                line.resolved_by = self.env.user
                line.resolved_date = fields.Datetime.now()
            else:
                line.resolved_by = False
                line.resolved_date = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._sync_resolved_stamp(vals)
        return super().create(vals_list)

    def write(self, vals):
        if 'state' in vals:
            self._sync_resolved_stamp(vals)
        return super().write(vals)

    def _sync_resolved_stamp(self, vals):
        """Keep resolved_by/resolved_date consistent even when state is
        set programmatically (import, API call, ...) rather than through
        the onchange above."""
        if vals.get('state') in RESOLVED_STATES:
            vals.setdefault('resolved_by', self.env.user.id)
            vals.setdefault('resolved_date', fields.Datetime.now())
        elif 'state' in vals and vals.get('state') not in RESOLVED_STATES:
            vals.setdefault('resolved_by', False)
            vals.setdefault('resolved_date', False)

    def copy_data(self, default=None):
        # Any duplication of a checklist line - whether triggered by a
        # manual "Duplicate" of the task, a project duplication, or (most
        # importantly) the recurrence engine creating the next occurrence
        # of a recurring task - should start back at "pending": the work
        # has not actually been redone (or re-confirmed not needed) yet
        # on the new copy.
        default = dict(default or {})
        default.setdefault('state', 'pending')
        default.setdefault('resolved_by', False)
        default.setdefault('resolved_date', False)
        return super().copy_data(default=default)
