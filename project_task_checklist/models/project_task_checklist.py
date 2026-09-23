from odoo import api, fields, models


class ProjectTaskChecklist(models.Model):
    _name = 'project.task.checklist'
    _description = 'Task Checklist'
    _order = 'sequence, id'

    name = fields.Char(required=True)
    task_id = fields.Many2one('project.task', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(default=10)
    # copy=True matters: Odoo's One2many fields default to copy=False, so
    # without it duplicating a checklist (or a task, below) silently drops
    # its items. See the note on ProjectTask.checklist_ids.
    line_ids = fields.One2many('project.task.checklist.line', 'checklist_id', string='Items', copy=True)
    template_id = fields.Many2one(
        'project.checklist.template', string='Source Template', ondelete='set null',
        help="Set automatically when this checklist was created from a template, or when it "
             "was saved as one - the accordion widget uses this to hide the 'save as template' "
             "button once a checklist is already linked to one.")

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

    # copy=True is what makes "Duplicate" (and project duplication) carry
    # the checklist over. Odoo's One2many fields default to copy=False, so
    # earlier versions of this module - which assumed the copy cascaded
    # automatically - never copied checklists on Duplicate at all. With
    # this set, the copy goes task -> checklists -> items, and
    # ProjectTaskChecklistLine.copy_data() resets every item to Pending.
    # It also means the recurrence engine (which builds each occurrence
    # from copy_data()) now carries checklists natively; the create()
    # backfill below stays as a safety net and skips any task that
    # already arrived with a checklist, so nothing is created twice.
    checklist_ids = fields.One2many('project.task.checklist', 'task_id', string='Checklists', copy=True)

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

    @api.model_create_multi
    def create(self, vals_list):
        # Backfill checklists onto tasks created by the recurrence engine.
        #
        # copy_data() on project.task.checklist.line (see above) resets
        # every item to Pending on any copy, which is exactly right for a
        # manual "Duplicate" or a project duplication - both of those go
        # through the standard copy()/copy_data() cascade, so the new
        # task's checklist_ids already arrive fully populated by the time
        # create() below runs.
        #
        # The recurrence engine (project.task.recurrence creating the next
        # occurrence of a repeating task) is a different story: it builds
        # the new task from a fixed whitelist of "recurring fields" and
        # creates it fresh, rather than copying the whole record - so a
        # third-party field like our checklist_ids was never in scope for
        # that cascade, and the new occurrence would otherwise land with
        # no checklist at all. Hooking create() itself - rather than trying
        # to override the recurrence engine's own internal method (whose
        # exact name/signature isn't something this module wants to
        # depend on) - covers both origins the same way, since every path
        # that creates a project.task record ultimately calls create():
        # if the checklist already arrived on the new task, we leave it
        # alone; if it didn't, we backfill it from the most recent other
        # task in the same recurrence series.
        tasks = super().create(vals_list)
        for task in tasks:
            if task.recurrence_id and not task.checklist_ids:
                sibling = self.search([
                    ('recurrence_id', '=', task.recurrence_id.id),
                    ('id', '!=', task.id),
                ], order='id desc', limit=1)
                for checklist in sibling.checklist_ids:
                    self.env['project.task.checklist'].create({
                        'task_id': task.id,
                        'name': checklist.name,
                        'sequence': checklist.sequence,
                        'template_id': checklist.template_id.id,
                        'line_ids': [
                            (0, 0, {
                                'name': line.name,
                                'sequence': line.sequence,
                                'state': 'pending',
                            })
                            for line in checklist.line_ids
                        ],
                    })
        return tasks
