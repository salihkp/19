# -*- coding: utf-8 -*-
from odoo import api, fields, models


class CropAnimalAssignment(models.Model):
    """
    Resource line to plan or record animal (livestock) usage
    linked to a crop process template or an actual task.
    """
    _name = 'crops.animals'
    _description = 'Crop Animal Assignment'
    _rec_name = 'partner_id'

    crops_tasks_template_id = fields.Many2one(
        'crops.tasks.template', string="Crops Tasks Template")
    task_id = fields.Many2one('project.task', string='Task')
    partner_id = fields.Many2one('res.partner', string="Animal", required=True)
    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True)
    quantity = fields.Float(string='Quantity', required=True)
    description = fields.Text(string='Description', required=True)
    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.company,
        help="Company this animal assignment belongs to.")
