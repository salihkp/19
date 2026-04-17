# -*- coding: utf-8 -*-
from odoo import api, fields, models


class CropFleetUsage(models.Model):
    """
    Resource line to plan or record vehicle (fleet) usage
    linked to a crop process template or an actual task.
    """
    _name = 'crops.fleet'
    _description = 'Crop Fleet Usage'
    _rec_name = 'vehicle_id'

    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', required=True)
    crops_tasks_template_id = fields.Many2one(
        'crops.tasks.template', string="Crops Tasks Template")
    task_id = fields.Many2one('project.task', string="Task")
    start_date = fields.Datetime(string='Start Date', required=True)
    end_date = fields.Datetime(string='End Date', required=True)
    quantity = fields.Float(string='Quantity', required=True)
    description = fields.Text(string='Description', required=True)
    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.company,
        help="Company this fleet usage belongs to.")
