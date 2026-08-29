# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ProjectTaskChecklist(models.Model):
    """One named checklist on a task. Items (project.task.checklist.line)
    are its direct children via line_ids - this is what makes the
    done/total progress reliably update live while checking items off on
    this record's own page: it's a plain "parent aggregates its own
    direct children" computation, the pattern Odoo's client-side onchange
    handles well.

    (An earlier design kept a single flat list of items directly on the
    task, using a marker field on each line to fake section headers -
    visually similar, but a section's count then depended on *sibling*
    rows within someone else's list, which Odoo's onchange does not
    reliably propagate live to the UI. This model exists specifically to
    avoid that class of problem, not just to work around it.)
    """
    _name = 'project.task.checklist'
    _description = 'Task Checklist'
    _order = 'sequence, id'

    task_id = fields.Many2one(
        'project.task', string='Task', required=True,
        ondelete='cascade', index=True)
    company_id = fields.Many2one(
        related='task_id.company_id', store=True, index=True, readonly=True)

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)

    template_id = fields.Many2one(
        'project.checklist.template', string='Created From Template',
        readonly=True, copy=True,
        help="The template this checklist's items were copied from, if "
             "any - purely informational. Editing the template afterward "
             "does not affect this checklist, and editing this checklist "
             "never touches the template.")

    line_ids = fields.One2many(
        'project.task.checklist.line', 'checklist_id', string='Items',
        copy=True)

    total_count = fields.Integer(
        string='Items', compute='_compute_progress')
    done_count = fields.Integer(
        string='Items Complete', compute='_compute_progress')
    not_needed_count = fields.Integer(
        string='Items Not Needed', compute='_compute_progress')
    pending_count = fields.Integer(
        string='Items Pending', compute='_compute_progress')
    progress = fields.Float(
        string='Progress', compute='_compute_progress',
        help="Percentage of items resolved - either Complete or Not "
             "Needed - out of the total.")
    progress_label = fields.Char(
        string='Progress Label', compute='_compute_progress',
        help="'resolved/total' as text, e.g. '2/5'.")

    @api.depends('line_ids.state')
    def _compute_progress(self):
        for checklist in self:
            lines = checklist.line_ids
            total = len(lines)
            done = len(lines.filtered(lambda l: l.state == 'done'))
            not_needed = len(lines.filtered(lambda l: l.state == 'not_needed'))
            resolved = done + not_needed
            checklist.total_count = total
            checklist.done_count = done
            checklist.not_needed_count = not_needed
            checklist.pending_count = total - resolved
            checklist.progress = (resolved / total * 100.0) if total else 0.0
            checklist.progress_label = '%d/%d' % (resolved, total)

    def action_reset_checklist(self):
        """Set every item on this checklist back to Pending."""
        self.line_ids.write({'state': 'pending'})
