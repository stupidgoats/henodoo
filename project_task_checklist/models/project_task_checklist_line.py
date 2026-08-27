# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ProjectTaskChecklistLine(models.Model):
    _name = 'project.task.checklist.line'
    _description = 'Project Task Checklist Item'
    _order = 'sequence, id'

    task_id = fields.Many2one(
        'project.task', string='Task', required=True,
        ondelete='cascade', index=True)
    company_id = fields.Many2one(
        related='task_id.company_id', store=True, index=True, readonly=True)

    sequence = fields.Integer(default=10)

    # A checklist line is either a real, checkable item (display_type is
    # False) or a non-checkable section header used to group items visually
    # (display_type == 'line_section'), mirroring the pattern Odoo already
    # uses for order lines elsewhere (e.g. sale.order.line).
    display_type = fields.Selection(
        [('line_section', 'Section')],
        default=False)

    name = fields.Char(required=True)

    is_done = fields.Boolean(string='Done')
    done_by = fields.Many2one(
        'res.users', string='Done by', readonly=True, copy=False)
    done_date = fields.Datetime(
        string='Done on', readonly=True, copy=False)

    section_progress = fields.Char(
        string='Section Progress', compute='_compute_section_progress',
        help="For a section row only: how many of the items under this "
             "section are done, e.g. '2/5'.")

    @api.depends(
        'display_type', 'sequence',
        'task_id.checklist_line_ids.display_type',
        'task_id.checklist_line_ids.is_done',
        'task_id.checklist_line_ids.sequence',
    )
    def _compute_section_progress(self):
        for line in self:
            line.section_progress = False
        self._refresh_section_progress(self.mapped('task_id'))

    def _refresh_section_progress(self, tasks):
        """Assign section_progress ('done/total') on every section row of
        each given task, based on the item rows that follow it up to the
        next section (or the end of the list).

        Walks the live task.checklist_line_ids recordset rather than
        indexing by id, so it works identically whether called from the
        stored compute (real, saved records) or from an onchange (where
        unsaved rows are NewId virtual records that don't behave like
        plain ints for id-based lookups).

        Called from two places on purpose: the compute below handles the
        normal dependency-triggered case (e.g. on load/save), but Odoo's
        client-side onchange only reliably re-triggers a field's compute
        for the row actually being edited - not for *sibling* rows whose
        compute merely depends on it (which is exactly this field's
        situation: a section's count depends on its item siblings, not on
        itself). Calling this explicitly from _onchange_is_done below is
        what makes the count update live as you check items, instead of
        only after save/reload.
        """
        for task in tasks:
            siblings = task.checklist_line_ids.sorted(key=lambda l: l.sequence)
            current_section = self.browse()
            current_items = self.browse()
            for sibling in siblings:
                if sibling.display_type == 'line_section':
                    if current_section:
                        current_section.section_progress = '%d/%d' % (
                            len(current_items.filtered('is_done')),
                            len(current_items))
                    current_section = sibling
                    current_items = self.browse()
                else:
                    current_items |= sibling
            if current_section:
                current_section.section_progress = '%d/%d' % (
                    len(current_items.filtered('is_done')), len(current_items))

    @api.onchange('is_done')
    def _onchange_is_done(self):
        for line in self:
            if line.is_done:
                line.done_by = self.env.user
                line.done_date = fields.Datetime.now()
            else:
                line.done_by = False
                line.done_date = False
        self._refresh_section_progress(self.mapped('task_id'))

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
