from odoo import api, fields, models


class ProjectTaskChecklist(models.Model):
    _name = 'project.task.checklist'
    _description = 'Task Checklist'
    _order = 'sequence, id'

    name = fields.Char(required=True)
    task_id = fields.Many2one('project.task', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(default=10)
    line_ids = fields.One2many('project.task.checklist.line', 'checklist_id', string='Items')

    total_count = fields.Integer(compute='_compute_counts')
    done_count = fields.Integer(compute='_compute_counts')
    not_needed_count = fields.Integer(compute='_compute_counts')
    pending_count = fields.Integer(compute='_compute_counts')
    progress = fields.Float(compute='_compute_counts')
    progress_label = fields.Char(compute='_compute_counts')

    @api.depends('line_ids.state')
    def _compute_counts(self):
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
            checklist.progress = (resolved / total * 100) if total else 0.0
            checklist.progress_label = "%d/%d" % (resolved, total)

    def action_reset_checklist(self):
        self.line_ids.write({'state': 'pending'})


class ProjectTaskChecklistLine(models.Model):
    _name = 'project.task.checklist.line'
    _description = 'Task Checklist Item'
    _order = 'sequence, id'

    name = fields.Char(required=True)
    checklist_id = fields.Many2one('project.task.checklist', required=True, ondelete='cascade', index=True)
    task_id = fields.Many2one(related='checklist_id.task_id', store=True, index=True, readonly=True)
    sequence = fields.Integer(default=10)
    state = fields.Selection([
        ('pending', 'Pending'),
        ('done', 'Complete'),
        ('not_needed', 'Not Needed'),
    ], default='pending', required=True)

    def action_reset_checklist(self):
        self.write({'state': 'pending'})

    def copy_data(self, default=None):
        # Checklist items always start fresh on a copy - whether that copy
        # comes from the recurrence engine creating the next occurrence, a
        # user clicking Duplicate on a task, or a whole project being
        # duplicated (which duplicates its tasks). A checklist represents
        # work still to be done on *this* instance of the task, so a
        # freshly created copy should never inherit a previous instance's
        # completed/not-needed state.
        vals_list = super().copy_data(default=default)
        for vals in vals_list:
            vals['state'] = 'pending'
        return vals_list


class ProjectTask(models.Model):
    _inherit = 'project.task'

    checklist_ids = fields.One2many('project.task.checklist', 'task_id', string='Checklists')

    checklist_total_count = fields.Integer(compute='_compute_checklist_stats', string='Checklist Items')
    checklist_done_count = fields.Integer(compute='_compute_checklist_stats', string='Checklist Items Done')
    checklist_not_needed_count = fields.Integer(compute='_compute_checklist_stats', string='Checklist Items Not Needed')
    checklist_pending_count = fields.Integer(compute='_compute_checklist_stats', string='Checklist Items Pending')
    checklist_progress = fields.Float(compute='_compute_checklist_stats', string='Checklist Progress')

    @api.depends('checklist_ids.line_ids.state')
    def _compute_checklist_stats(self):
        for task in self:
            lines = task.checklist_ids.line_ids
            total = len(lines)
            done = len(lines.filtered(lambda l: l.state == 'done'))
            not_needed = len(lines.filtered(lambda l: l.state == 'not_needed'))
            resolved = done + not_needed
            task.checklist_total_count = total
            task.checklist_done_count = done
            task.checklist_not_needed_count = not_needed
            task.checklist_pending_count = total - resolved
            task.checklist_progress = (resolved / total * 100) if total else 0.0

    def action_reset_checklist(self):
        self.checklist_ids.action_reset_checklist()
