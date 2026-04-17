# -*- coding: utf-8 -*-
from odoo import api, fields, models


class CropsTasksTemplate(models.Model):
    """
    Template linking a project task to the resources (equipment, animals, fleet)
    that should be associated when the task is copied into an operational project.
    """
    _name = 'crops.tasks.template'
    _description = 'Crop Process Template'
    _rec_name = 'task_id'

    task_id = fields.Many2one('project.task', string="Task", required=True)
    crop_id = fields.Many2one('farmer.location.crops', string="Crop", required=True)
    animal_ids = fields.One2many(
        'crops.animals', 'crops_tasks_template_id', string="Animals")
    fleet_ids = fields.One2many(
        'crops.fleet', 'crops_tasks_template_id', string="Fleets")
    equipment_ids = fields.Many2many('maintenance.equipment', string='Equipments')
    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.company,
        help="Company this process template belongs to.")
