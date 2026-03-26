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
    _description = "Crop Requests"
    number = fields.Char(string='Number',readonly=True,copy=False)
    name = fields.Char(string='Name',required=True)
    description = fields.Text(string='Description')
    internal_note = fields.Text(string='Internal Notes')
    state = fields.Selection(
        [('new', 'New'),('confirm', 'Confirmed'),('in_progress', 'In Progress'),('done','Done'),('cancel','Cancel')],
        string="State",default='new',required=True)
    start_date = fields.Date(string='Start Date',required=True)
    end_date = fields.Date(string='End Date',required=True)
    company_id = fields.Many2one('res.company',string="Company",required=True,default=lambda self: self.env.user.company_id)
    user_id = fields.Many2one('res.users',string="Supervisor",default=lambda self: self.env.user,required=True)
    project_id = fields.Many2one('project.project',string="Project",copy=False)
    responsible_user_id = fields.Many2one('res.users',string="Responsible User",
                                          default=lambda self: self.env.user,required=True,)
    duration_days = fields.Integer(string="Duration (days)",compute="_compute_duration_days",
                                   store=True,help="Inclusive days between Start and End dates.")
    days_to_start = fields.Integer(string="Days to Start",compute="_compute_days_to_milestones",
                                   help="Negative if the start date is in the past.")
    days_to_end = fields.Integer(string="Days to End",compute="_compute_days_to_milestones",
                                 help="Negative if the end date is in the past.")
    reminder_days_before_start = fields.Integer(string="Remind Before Start (days)",default=7,
                                                help="Create a To-Do this many days before the start date.")
    reminder_days_before_end = fields.Integer(string="Remind Before End (days)",
                                              default=3,help="Create a To-Do this many days before the end date.")
    crop_ids = fields.Many2one('farmer.location.crops',string='Crop',required=True)
    task_count = fields.Integer(compute='_compute_task_counter',string="Task Count")
    equipment_count = fields.Integer(compute='_compute_equipment_counter',string="Equipment Count")
    animal_count = fields.Integer(compute='_compute_animal_counter',string="Animal Count")
    dieases_count = fields.Integer(compute='_compute_dieases_counter',string="Dieases Count")
    fleet_count = fields.Integer(compute='_compute_fleet_counter',string="Fleet Count")
    project_count = fields.Integer(compute='_compute_project_counter',string="Project Count")
    @api.constrains("start_date", "end_date")
    def _check_dates(self):
        """Ensure end date is not before start date."""
        for rec in self:
            if rec.start_date and rec.end_date and rec.end_date < rec.start_date:
                raise ValidationError("End Date must be on or after Start Date.")
    def _compute_task_counter(self):
        for rec in self:
            rec.task_count = self.env['project.task'].search_count([('project_id','in', self.project_id.ids)])
    def _compute_project_counter(self):
        for rec in self:
            rec.project_count = self.env['project.project'].search_count([('id', 'in', self.project_id.ids)])
    def _compute_fleet_counter(self):
        fleets = []
        for rec in self:
            rec.fleet_count = 0
            for crop in rec.crop_ids:
                for crop_temp in crop.crop_task_ids:
                    for fleet in crop_temp.fleet_ids:
                        fleets.append(fleet.id)
                        rec.fleet_count = self.env['crops.fleet'].search_count([('id','in', fleets)])
    def _compute_dieases_counter(self):
        dieaseses = []
        for rec in self:
            rec.dieases_count = 0
            for crop in rec.crop_ids:
                for dieases in crop.crops_dieases_ids:
                    dieaseses.append(dieases.id)
                    rec.dieases_count = self.env['crops.dieases'].search_count([('id','in', dieaseses)])
    def _compute_equipment_counter(self):
        equipments = []
        for rec in self:
            rec.equipment_count = 0
            for crop in rec.crop_ids:
                for crop_temp in crop.crop_task_ids:
                    for equipment in crop_temp.equipment_ids:
                        equipments.append(equipment.id)
                        rec.equipment_count = self.env['maintenance.equipment'].search_count([('id','in', equipments)])
    def _compute_animal_counter(self):
        animals = []
        for rec in self:
            rec.animal_count = 0
            for crop in rec.crop_ids:
                for crop_temp in crop.crop_task_ids:
                    for animal in crop_temp.animal_ids:
                        animals.append(animal.id)
                        rec.animal_count = self.env['crops.animals'].search_count([('id','in', animals)])
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
        """
        self.ensure_one()
        activity_type = self.env.ref("mail.mail_activity_data_todo")
        model_name = "farmer.cropping.request"
        # Start reminder
        if self.start_date and self.reminder_days_before_start >= 0:
            start_deadline = self.start_date - relativedelta(days=self.reminder_days_before_start)
            self.env["mail.activity"].create({
                "res_model": model_name,
                "res_id": self.id,
                "activity_type_id": activity_type.id,
                "user_id": self.responsible_user_id.id or self.user_id.id,
                "summary": f"Prepare crop start: {self.name}",
                "note": f"Crop {self.name} starts on {self.start_date}.",
                "date_deadline": start_deadline,})
        # End reminder
        if self.end_date and self.reminder_days_before_end >= 0:
            end_deadline = self.end_date - relativedelta(days=self.reminder_days_before_end)
            self.env["mail.activity"].create({
                "res_model": model_name,
                "res_id": self.id,
                "activity_type_id": activity_type.id,
                "user_id": self.responsible_user_id.id or self.user_id.id,
                "summary": f"Prepare crop closure: {self.name}",
                "note": f"Crop {self.name} ends on {self.end_date}.",
                "date_deadline": end_deadline,})
        return True
    def action_view_project_request(self):
        """Open projects linked to this request."""
        action = self.env.ref('kazn_odoo_agriculture.action_view_farmer_cropping_project').sudo().read()[0]
        action['domain'] = [('id','in', self.project_id.ids)]
        return action
    def action_view_task_request(self):
        """Open tasks of the project's cropping request."""
        action = self.env.ref('kazn_odoo_agriculture.action_view_farmer_cropping_task').sudo().read()[0]
        action['domain'] = [('project_id','in', self.project_id.ids)]
        return action
    def action_view_animal_request(self):
        """Open animal assignments linked via crop templates."""
        action = self.env.ref('kazn_odoo_agriculture.action_crops_animals').sudo().read()[0]
        animals = []
        for rec in self:
            for crop in rec.crop_ids:
                for crop_temp in crop.crop_task_ids:
                    for animal in crop_temp.animal_ids:
                        animals.append(animal.id)
        action['domain'] = [('id','in', animals)]
        return action
    def action_view_fleet_request(self):
        """Open fleet usages linked via crop templates."""
        action = self.env.ref('kazn_odoo_agriculture.action_crops_fleet').sudo().read()[0]
        fleets = []
        for rec in self:
            for crop in rec.crop_ids:
                for crop_temp in crop.crop_task_ids:
                    for fleet in crop_temp.fleet_ids:
                        fleets.append(fleet.id)
        action['domain'] = [('id','in', fleets)]
        return action
    def action_view_dieases_request(self):
        """Open diseases registered on the crop (technical name preserved)."""
        action = self.env.ref('kazn_odoo_agriculture.action_crops_dieases').sudo().read()[0]
        dieaseses = []
        for rec in self:
            for crop in rec.crop_ids:
                for dieases in crop.crops_dieases_ids:
                    dieaseses.append(dieases.id)
        action['domain'] = [('id','in', dieaseses)]
        return action
    def action_view_equipment_request(self):
        """Open equipment planned on templates linked to the crop."""
        action = self.env.ref('maintenance.hr_equipment_action').sudo().read()[0]
        equipments = []
        for rec in self:
            for crop in rec.crop_ids:
                for crop_temp in crop.crop_task_ids:
                    for equipment in crop_temp.equipment_ids:
                        equipments.append(equipment.id)
        action['domain'] = [('id','in', equipments)]
        return action
    @api.model_create_multi
    def create(self, vals_list):
        """
        Assign the next sequence number on creation.
        Note: loop is kept minimal; business logic unchanged.
        """
        for vals in vals_list:
            vals['number'] = self.env['ir.sequence'].next_by_code('farmer.cropping.request')
            return super(FarmerCroppingRequest,self).create(vals_list)
    def action_in_progress(self , vals=None):
        """
        Move to 'In Progress', create a project, and copy planned tasks along
        with their equipment/animals/fleet into the new project.
        """
        self.write({'state': 'in_progress'})
        project_vals = {'name': self.name + '-' + self.number,'company_id': self.company_id.id,
                        'alias_id': 1,'custom_request_id': self.id}
        project_id = self.env['project.project'].create(project_vals)
        for rec in self:
            rec.project_id = project_id.id
            crop_ids = rec.crop_ids
            crop_task_ids = crop_ids.mapped('crop_task_ids')
            my_dict = {}
            for x in crop_task_ids:
                my_dict[x.task_id] = x
            task_ids = crop_task_ids.mapped('task_id')
            old = {}
            pp = []
            for task in task_ids:
                default = {'project_id': project_id.id,'name' : task.name + '-' + rec.number,
                           'custom_request_id': rec.id,'is_cropping_request': True,}
                duplicate_task_ids = task.copy(default)
                old[duplicate_task_ids.id] = task
                pp.append(duplicate_task_ids)
            for d in pp:
                equipment_lst = []
                for x1 in my_dict[old[d.id]].equipment_ids:
                    equipment_lst.append(x1.id)
                for mm in my_dict[old[d.id]].animal_ids:
                    default = {'crops_tasks_template_id':False, 'task_id':d.id}
                    fu = mm.copy(default)
                for fff in my_dict[old[d.id]].fleet_ids:
                    default = {'crops_tasks_template_id':False, 'task_id':d.id}
                    fu1 = fff.copy(default)
                d.equipment_ids = equipment_lst
    def action_confirm(self):
        return self.write({'state': 'confirm'})
    def action_done(self):
        return self.write({'state': 'done'})
    def action_cancel(self):
        return self.write({'state': 'cancel'})
    def action_reset_to_draft(self):
        return self.write({'state': 'new'})