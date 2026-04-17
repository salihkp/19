# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError
from odoo import api, fields, models


class FarmerCroppingRequest(models.Model):
    """
    Central record for a seasonal crop operation. Tracks workflow, company/users,
    links to the crop definition, and spawns a project with tasks/resources.
    """
    _name = 'farmer.cropping.request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'
    _description = "Crop Request"

    number = fields.Char(string='Number', readonly=True, copy=False)
    name = fields.Char(string='Name', required=True)
    description = fields.Text(string='Description')
    internal_note = fields.Text(string='Internal Notes')
    state = fields.Selection(
        [('new', 'New'), ('confirm', 'Confirmed'), ('in_progress', 'In Progress'),
         ('done', 'Done'), ('cancel', 'Cancel')],
        string="State", default='new', required=True)
    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True)
    company_id = fields.Many2one(
        'res.company', string="Company", required=True,
        default=lambda self: self.env.company)
    user_id = fields.Many2one(
        'res.users', string="Supervisor",
        default=lambda self: self.env.user, required=True)
    project_id = fields.Many2one('project.project', string="Project", copy=False)
    responsible_user_id = fields.Many2one(
        'res.users', string="Crop Responsible",
        default=lambda self: self.env.user, required=True,
        help="User responsible for executing and overseeing this crop request.")
    duration_days = fields.Integer(
        string="Duration (days)", compute="_compute_duration_days",
        store=True, help="Inclusive days between Start and End dates.")
    days_to_start = fields.Integer(
        string="Days to Start", compute="_compute_days_to_milestones",
        help="Negative if the start date is in the past.")
    days_to_end = fields.Integer(
        string="Days to End", compute="_compute_days_to_milestones",
        help="Negative if the end date is in the past.")
    reminder_days_before_start = fields.Integer(
        string="Remind Before Start (days)", default=7,
        help="Create a To-Do this many days before the start date.")
    reminder_days_before_end = fields.Integer(
        string="Remind Before End (days)", default=3,
        help="Create a To-Do this many days before the end date.")
    crop_ids = fields.Many2one('farmer.location.crops', string='Crop', required=True)
    task_count = fields.Integer(compute='_compute_task_counter', string="Task Count")
    equipment_count = fields.Integer(
        compute='_compute_equipment_counter', string="Equipment Count")
    animal_count = fields.Integer(
        compute='_compute_animal_counter', string="Animal Count")
    dieases_count = fields.Integer(
        compute='_compute_dieases_counter', string="Dieases Count")
    fleet_count = fields.Integer(
        compute='_compute_fleet_counter', string="Fleet Count")
    project_count = fields.Integer(
        compute='_compute_project_counter', string="Project Count")

    @api.constrains("start_date", "end_date")
    def _check_dates(self):
        """Ensure end date is not before start date."""
        for rec in self:
            if rec.start_date and rec.end_date and rec.end_date < rec.start_date:
                raise ValidationError("End Date must be on or after Start Date.")

    def _compute_task_counter(self):
        for rec in self:
            rec.task_count = self.env['project.task'].search_count(
                [('project_id', '=', rec.project_id.id)]) if rec.project_id else 0

    def _compute_project_counter(self):
        for rec in self:
            rec.project_count = 1 if rec.project_id else 0

    def _compute_fleet_counter(self):
        """Count fleet records linked via crop process templates."""
        for rec in self:
            fleets = []
            for crop_temp in rec.crop_ids.crop_task_ids:
                fleets.extend(crop_temp.fleet_ids.ids)
            rec.fleet_count = self.env['crops.fleet'].search_count(
                [('id', 'in', fleets)])

    def _compute_dieases_counter(self):
        """Count disease records linked to the crop."""
        for rec in self:
            dieaseses = rec.crop_ids.crops_dieases_ids.ids
            rec.dieases_count = self.env['crops.dieases'].search_count(
                [('id', 'in', dieaseses)])

    def _compute_equipment_counter(self):
        """Count equipment records linked via crop process templates."""
        for rec in self:
            equipments = []
            for crop_temp in rec.crop_ids.crop_task_ids:
                equipments.extend(crop_temp.equipment_ids.ids)
            rec.equipment_count = self.env['maintenance.equipment'].search_count(
                [('id', 'in', equipments)])

    def _compute_animal_counter(self):
        """Count animal records linked via crop process templates."""
        for rec in self:
            animals = []
            for crop_temp in rec.crop_ids.crop_task_ids:
                animals.extend(crop_temp.animal_ids.ids)
            rec.animal_count = self.env['crops.animals'].search_count(
                [('id', 'in', animals)])

    @api.depends("start_date", "end_date")
    def _compute_duration_days(self):
        """Compute inclusive duration between start and end dates."""
        for rec in self:
            if rec.start_date and rec.end_date:
                rec.duration_days = (rec.end_date - rec.start_date).days + 1
            else:
                rec.duration_days = 0

    def _compute_days_to_milestones(self):
        """Compute the countdown to start and end dates."""
        today = fields.Date.context_today(self)
        for rec in self:
            rec.days_to_start = (rec.start_date - today).days if rec.start_date else 0
            rec.days_to_end = (rec.end_date - today).days if rec.end_date else 0

    def action_schedule_reminders(self):
        """
        Create mail activities (To-Do) for the responsible user:
         - Before start date
         - Before end date

        Workflow:
            1. Resolve the To-Do activity type via xml ref.
            2. Create a start-date reminder if start_date is set.
            3. Create an end-date reminder if end_date is set.

        Args:
            None — operates on self (single record).

        Returns:
            True
        """
        self.ensure_one()
        activity_type = self.env.ref("mail.mail_activity_data_todo")
        model_id = self.env["ir.model"]._get_id("farmer.cropping.request")
        assigned_user_id = self.responsible_user_id.id or self.user_id.id

        def _create_reminder_if_missing(summary, note, deadline):
            existing = self.env["mail.activity"].search_count([
                ("res_model_id", "=", model_id),
                ("res_id", "=", self.id),
                ("activity_type_id", "=", activity_type.id),
                ("user_id", "=", assigned_user_id),
                ("summary", "=", summary),
                ("date_deadline", "=", deadline),
            ])
            if not existing:
                self.env["mail.activity"].create({
                    "res_model_id": model_id,
                    "res_id": self.id,
                    "activity_type_id": activity_type.id,
                    "user_id": assigned_user_id,
                    "summary": summary,
                    "note": note,
                    "date_deadline": deadline,
                })

        if self.start_date and self.reminder_days_before_start >= 0:
            start_deadline = self.start_date - relativedelta(days=self.reminder_days_before_start)
            _create_reminder_if_missing(
                summary=f"Prepare crop start: {self.name}",
                note=f"Crop {self.name} starts on {self.start_date}.",
                deadline=start_deadline,
            )
        if self.end_date and self.reminder_days_before_end >= 0:
            end_deadline = self.end_date - relativedelta(days=self.reminder_days_before_end)
            _create_reminder_if_missing(
                summary=f"Prepare crop closure: {self.name}",
                note=f"Crop {self.name} ends on {self.end_date}.",
                deadline=end_deadline,
            )
        return True

    def action_view_project_request(self):
        """Open projects linked to this request."""
        action = self.env.ref(
            'kazn_odoo_agriculture.action_view_farmer_cropping_project').sudo().read()[0]
        action['domain'] = [('id', 'in', self.project_id.ids)]
        return action

    def action_view_task_request(self):
        """Open tasks of the project's cropping request."""
        action = self.env.ref(
            'kazn_odoo_agriculture.action_view_farmer_cropping_task').sudo().read()[0]
        action['domain'] = [('project_id', 'in', self.project_id.ids)]
        return action

    def action_view_animal_request(self):
        """Open animal assignments linked via crop templates."""
        action = self.env.ref(
            'kazn_odoo_agriculture.action_crops_animals').sudo().read()[0]
        animals = []
        for crop_temp in self.crop_ids.crop_task_ids:
            animals.extend(crop_temp.animal_ids.ids)
        action['domain'] = [('id', 'in', animals)]
        return action

    def action_view_fleet_request(self):
        """Open fleet usages linked via crop templates."""
        action = self.env.ref(
            'kazn_odoo_agriculture.action_crops_fleet').sudo().read()[0]
        fleets = []
        for crop_temp in self.crop_ids.crop_task_ids:
            fleets.extend(crop_temp.fleet_ids.ids)
        action['domain'] = [('id', 'in', fleets)]
        return action

    def action_view_dieases_request(self):
        """Open diseases registered on the crop (technical name preserved)."""
        action = self.env.ref(
            'kazn_odoo_agriculture.action_crops_dieases').sudo().read()[0]
        action['domain'] = [('id', 'in', self.crop_ids.crops_dieases_ids.ids)]
        return action

    def action_view_equipment_request(self):
        """Open equipment planned on templates linked to the crop."""
        action = self.env.ref('maintenance.hr_equipment_action').sudo().read()[0]
        equipments = []
        for crop_temp in self.crop_ids.crop_task_ids:
            equipments.extend(crop_temp.equipment_ids.ids)
        action['domain'] = [('id', 'in', equipments)]
        return action

    @api.model_create_multi
    def create(self, vals_list):
        """
        Assign the next sequence number on creation for every record in the batch.

        Args:
            vals_list (list): List of value dicts for each record to create.

        Returns:
            FarmerCroppingRequest: Created recordset.
        """
        for vals in vals_list:
            if not vals.get('number'):
                vals['number'] = self.env['ir.sequence'].next_by_code(
                    'farmer.cropping.request')
        return super(FarmerCroppingRequest, self).create(vals_list)

    def action_in_progress(self):
        """
        Move to 'In Progress', create a project, and copy planned tasks along
        with their equipment/animals/fleet into the new project.

        Workflow:
            1. Ensure single record context.
            2. Write state to 'in_progress'.
            3. Create a project named after this request.
            4. For each task template on the crop, copy the task into the project.
            5. Copy animal and fleet lines onto each duplicated task.
            6. Assign equipment list to each duplicated task.

        Args:
            None — operates on self (single record).

        Returns:
            None
        """
        self.ensure_one()
        if self.project_id:
            raise ValidationError("A project is already linked to this crop request.")
        self.write({'state': 'in_progress'})
        project_vals = {
            'name': self.name + '-' + self.number,
            'company_id': self.company_id.id,
            'custom_request_id': self.id,
        }
        project_id = self.env['project.project'].create(project_vals)
        self.project_id = project_id.id
        crop_task_ids = self.crop_ids.crop_task_ids
        template_by_task = {tmpl.task_id.id: tmpl for tmpl in crop_task_ids if tmpl.task_id}
        task_ids = crop_task_ids.mapped('task_id')
        duplicated = []
        original_map = {}
        for task in task_ids:
            default = {
                'project_id': project_id.id,
                'name': task.name + '-' + self.number,
                'custom_request_id': self.id,
                'is_cropping_request': True,
            }
            dup = task.copy(default)
            original_map[dup.id] = task.id
            duplicated.append(dup)
        for dup in duplicated:
            tmpl = template_by_task.get(original_map[dup.id])
            if not tmpl:
                continue
            for animal in tmpl.animal_ids:
                animal.copy({'crops_tasks_template_id': False, 'task_id': dup.id})
            for fleet in tmpl.fleet_ids:
                fleet.copy({'crops_tasks_template_id': False, 'task_id': dup.id})
            dup.equipment_ids = [(6, 0, tmpl.equipment_ids.ids)]

    def action_confirm(self):
        return self.write({'state': 'confirm'})

    def action_done(self):
        return self.write({'state': 'done'})

    def action_cancel(self):
        return self.write({'state': 'cancel'})

    def action_reset_to_draft(self):
        return self.write({'state': 'new'})
