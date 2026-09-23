from odoo import fields, models


class ProjectChecklistTemplate(models.Model):
    _name = 'project.checklist.template'
    _description = 'Checklist Template'
    _order = 'name'

    name = fields.Char(required=True)
    line_ids = fields.One2many('project.checklist.template.line', 'template_id', string='Items')


class ProjectChecklistTemplateLine(models.Model):
    _name = 'project.checklist.template.line'
    _description = 'Checklist Template Item'
    _order = 'sequence, id'

    name = fields.Char(required=True)
    template_id = fields.Many2one('project.checklist.template', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)


class ProjectChecklistTemplateApply(models.TransientModel):
    _name = 'project.checklist.template.apply'
    _description = 'Apply Checklist Template'

    task_id = fields.Many2one('project.task', required=True)
    template_id = fields.Many2one('project.checklist.template', required=True)

    def action_apply(self):
        self.ensure_one()
        return self.env['project.task.checklist'].create({
            'task_id': self.task_id.id,
            'name': self.template_id.name,
            'template_id': self.template_id.id,
            'line_ids': [
                (0, 0, {'name': line.name, 'sequence': line.sequence})
                for line in self.template_id.line_ids
            ],
        })
