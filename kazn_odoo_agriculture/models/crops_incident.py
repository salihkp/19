from odoo import api, fields, models
class CropsIncident(models.Model):
    """
    Field incident logged against a crop and (optionally) a task.
    """
    _name = 'crops.incident'
    crop_id = fields.Many2one('farmer.location.crops',string='Crop',required=True)
    task_id = fields.Many2one('project.task',string='Task',required=True)
    name = fields.Char(string='Name',required=True)
    datetime = fields.Datetime(string='Datetime',required=True)
    location_id = fields.Many2one('res.partner',string='Location',required=True)
    description = fields.Char(string='Description',required=True)