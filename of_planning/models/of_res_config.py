# -*- coding: utf-8 -*-

import time
import datetime
from dateutil.relativedelta import relativedelta

import odoo
from odoo import SUPERUSER_ID
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class OfResCompany(models.Model):
    _inherit = "res.company"

    display_realtime_gantt = fields.Boolean(string=u"Afficher les dates réelles d'intervention dans le planning Intervention par employé")

class OfInterventionSettings(models.TransientModel):
    _name = 'of.intervention.settings'
    _inherit = 'res.config.settings'

    company_id = fields.Many2one('res.company', string='Company', required=True,
        default=lambda self: self.env.user.company_id)

    display_realtime_gantt = fields.Boolean(string=u"Afficher les dates réelles d'intervention dans le planning Intervention par employé", related='company_id.display_realtime_gantt')

    # TODO : Voir si il serait préfèrable de mettre certains champ dans la société
    display_timer = fields.Boolean(string='Display Timer on application',
                                   help='Enable or disable the timer on the application.')
    use_signature = fields.Boolean(string='Use signature on application',
                                   help='Enable or disable signatures on the application')
    mandatory_function = fields.Boolean(string='The Customer function field is mandatory on application',
                                        help='Force Customer function on the application')
    use_photos = fields.Boolean(string='Use photos on application',
                                help='Enable or disable photos on the application.')
    supp_finish_interv = fields.Boolean(string='Enable suppression of a finished intervention',
                                        help='Enable or disable suppression of a finished intervention.')
    multi_started_interv = fields.Boolean(string='Enable to start several interventions simultaneously',
                                          help='Enable or disable to start several interventions simultaneously.')
    use_sale_order = fields.Boolean(string='Use sale order on application',
                                    help='Enable or disable sale order on the application')
    auto_assign_interv = fields.Boolean(string='Auto assigned the technician when created an intervention on application',
                                        help='Enable or disable auto assigned the technician when created an intervention on application')
    generate_recurent = fields.Boolean(string='Generate recurent intervention only after finish one',
                                       help='Enable or disable the generation of recurent intervention only after finish one')
    allow_same_time_interv = fields.Boolean(string='Enable to affect several interventions for same employee in same time',
                                            help='Enable or disable the affectation of several interventions for same employee in same time')
    allow_reminder_push_notif_stop = fields.Boolean(string='Enable to send reminder stop for employee',
                                                    help='Enable or disable the push notification reminder for stop intervention')

    @api.multi
    def set_display_timer_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'display_timer', self.display_timer)

    @api.multi
    def set_use_signature_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'use_signature', self.use_signature)

    @api.multi
    def set_mandatory_function_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'mandatory_function', self.mandatory_function)

    @api.multi
    def set_use_photos_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'use_photos', self.use_photos)

    @api.multi
    def set_supp_finish_interv_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'supp_finish_interv', self.supp_finish_interv)

    @api.multi
    def set_multi_started_interv_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'multi_started_interv', self.multi_started_interv)

    @api.multi
    def set_use_sale_order_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'use_sale_order', self.use_sale_order)

    @api.multi
    def set_auto_assign_interv_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'auto_assign_interv', self.auto_assign_interv)

    @api.multi
    def set_generate_recurent_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'generate_recurent', self.generate_recurent)

    @api.multi
    def set_allow_same_time_interv_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'allow_same_time_interv', self.allow_same_time_interv)

    @api.multi
    def set_allow_reminder_push_notif_stop_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'allow_reminder_push_notif_stop', self.allow_reminder_push_notif_stop)

