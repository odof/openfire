# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models

from .res_config_settings import SELECTION_SEARCH_MODES, SELECTION_SEARCH_TYPES


class OFTourAppointmentTemplate(models.Model):
    _name = 'of.tour.appointment.template'
    _description = 'Appointment Template'

    name = fields.Char(required=True)
    employee_ids = fields.Many2many(comodel_name='hr.employee', string="Operator(s)")
    task_id = fields.Many2one(comodel_name='of.planning.task', string="Task")
    template_id = fields.Many2one(comodel_name='of.planning.intervention.template', string="Intervention template")
    search_type = fields.Selection(selection=SELECTION_SEARCH_TYPES, string="Search type")
    search_mode = fields.Selection(selection=SELECTION_SEARCH_MODES, string="Search mode")
    access_user_ids = fields.Many2many(
        comodel_name='res.users',
        relation='of_tour_appointment_template_access_users_rel',
        column1='template_id',
        column2='user_id',
        string="Access for",
        help="Users who can use this template to create appointments",
    )
    default_user_ids = fields.Many2many(
        comodel_name='res.users',
        relation='of_tour_appointment_template_default_users_rel',
        column1='template_id',
        column2='user_id',
        string="Default for",
        help="Users for whom this template will be used by default",
    )
