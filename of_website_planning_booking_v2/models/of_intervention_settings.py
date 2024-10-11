# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.of_planning_tournee.models.of_intervention_settings import (
    SELECTION_SEARCH_MODES,
    SELECTION_SEARCH_TYPES,
)


class OFInterventionSettings(models.TransientModel):
    _inherit = 'of.intervention.settings'

    @api.model
    def _auto_init(self):
        super(OFInterventionSettings, self)._auto_init()
        if self.env['ir.values'].get_default('of.intervention.settings', 'booking_open_new_customer') is None:
            self.env['ir.values'].set_default('of.intervention.settings', 'booking_open_new_customer', True)
        if self.env['ir.values'].get_default('of.intervention.settings', 'booking_use_partner_company') is None:
            self.env['ir.values'].set_default('of.intervention.settings', 'booking_use_partner_company', True)
        if self.env['ir.values'].get_default('of.intervention.settings', 'booking_intervention_company_id') is None:
            self.env['ir.values'].set_default(
                'of.intervention.settings', 'booking_intervention_company_id',
                self._default_booking_intervention_company_id())
        if self.env['ir.values'].get_default('of.intervention.settings', 'booking_opened_day_ids') is None:
            self.env['ir.values'].set_default(
                'of.intervention.settings', 'booking_opened_day_ids', self._default_opened_day_ids())
        if self.env['ir.values'].get_default('of.intervention.settings', 'booking_open_days_number') is None:
            self.env['ir.values'].set_default('of.intervention.settings', 'booking_open_days_number', 60)
        if self.env['ir.values'].get_default('of.intervention.settings', 'booking_search_mode') is None:
            self.env['ir.values'].set_default('of.intervention.settings', 'booking_search_mode', 'oneway')
        if self.env['ir.values'].get_default('of.intervention.settings', 'booking_search_type') is None:
            self.env['ir.values'].set_default('of.intervention.settings', 'booking_search_type', 'distance')
        if self.env['ir.values'].get_default('of.intervention.settings', 'booking_search_max_criteria') is None:
            self.env['ir.values'].set_default('of.intervention.settings', 'booking_search_max_criteria', 20)
        if self.env['ir.values'].get_default('of.intervention.settings', 'booking_allow_empty_days') is None:
            self.env['ir.values'].set_default('of.intervention.settings', 'booking_allow_empty_days', True)
        if self.env['ir.values'].get_default('of.intervention.settings', 'booking_intervention_state') is None:
            self.env['ir.values'].set_default('of.intervention.settings', 'booking_intervention_state', 'draft')
        if self.env['ir.values'].get_default('of.intervention.settings', 'booking_display_price') is None:
            self.env['ir.values'].set_default('of.intervention.settings', 'booking_display_price', True)
        if self.env['ir.values'].get_default('of.intervention.settings', 'website_edit_days_limit') is None:
            self.env['ir.values'].set_default('of.intervention.settings', 'website_edit_days_limit', 14)
        if self.env['ir.values'].get_default('of.intervention.settings', 'booking_morning_hours_label') is None:
            self.env['ir.values'].set_default(
                'of.intervention.settings', 'booking_morning_hours_label', u"8h00 - 13h00")
        if self.env['ir.values'].get_default('of.intervention.settings', 'booking_afternoon_hours_label') is None:
            self.env['ir.values'].set_default(
                'of.intervention.settings', 'booking_afternoon_hours_label', u"14h00 - 18h00")

    def _default_website(self):
        return self.env['website'].search([], limit=1)

    def _default_booking_intervention_company_id(self):
        website = self.website_id
        if not website:
            website = self.env['website'].search([], limit=1)
        return website.company_id.id

    def _default_opened_day_ids(self):
        days = self.env['of.jours'].search([('numero', '<', 6)], order='numero')
        res = [day.id for day in days]
        return res

    website_id = fields.Many2one(
        comodel_name='website', string=u"Site web", default=lambda r: r._default_website(), required=True)
    booking_open_new_customer = fields.Boolean(string=u"Ouvrir la prise de RDV aux nouveaux clients", default=True)
    booking_use_partner_company = fields.Boolean(
        string=u"Utilise la société du partenaire pour les clients existants", default=True)
    booking_intervention_company_id = fields.Many2one(
        comodel_name='res.company', string=u"Société des RDV",
        default=lambda r: r._default_booking_intervention_company_id()
    )
    booking_company_dependent = fields.Boolean(string=u"Définir une configuration spécifique à cette société")
    booking_opened_day_ids = fields.Many2many(
        comodel_name='of.jours', string=u"Jours ouverts", default=lambda r: r._default_opened_day_ids())
    booking_employee_ids = fields.Many2many(
        comodel_name='hr.employee', relation='of_intervention_settings_booking_employee_rel',
        string=u"Techniciens disponibles",
        domain=['|', ('of_est_intervenant', '=', True), ('of_est_commercial', '=', True)])
    booking_open_days_number = fields.Integer(
        string=u"Nombre de jours ouverts à la réservation (max 180 jours)", default=60)
    booking_search_mode = fields.Selection(selection=SELECTION_SEARCH_MODES, string=u"Mode de recherche", required=True)
    booking_search_type = fields.Selection(selection=SELECTION_SEARCH_TYPES, string=u"Type de recherche", required=True)
    booking_search_max_criteria = fields.Integer(string=u"Critère de recherche max", required=True)
    booking_allow_empty_days = fields.Boolean(
        string=u"Autorise la réservation de créneau sur des journées vierges", default=True)
    booking_intervention_state = fields.Selection(
        selection=[
            ('draft', u"Brouillon"),
            ('confirm', u"Confirmé")
        ], string=u"État des RDV à la prise de RDV en ligne", default='draft', required=True)
    booking_display_price = fields.Boolean(string=u"Afficher le prix de la prestation", default=True)
    website_edit_days_limit = fields.Integer(string=u"Limite de modifications", default=14)
    booking_terms_file = fields.Binary(
        string=u"Fichier PDF des Conditions Générales de Vente",
        filename='booking_terms_filename',
        compute='_compute_booking_terms_file',
        inverse='_inverse_booking_terms_file')
    booking_terms_filename = fields.Char(
        string=u"Nom du fichier PDF des Conditions Générales de Vente",
        compute='_compute_booking_terms_file',
        inverse='_inverse_booking_terms_filename')
    booking_morning_hours_label = fields.Char(string=u"Libellé horaires matin")
    booking_afternoon_hours_label = fields.Char(string=u"Libellé horaires après-midi")
    booking_validation_note = fields.Html(string=u"Notes de confirmation de RDV")

    @api.constrains('booking_open_days_number')
    def _check_booking_open_days_number_constraint(self):
        for record in self:
            if record.booking_open_days_number < 0:
                raise ValidationError(u"Vous ne pouvez pas avoir un nombre de jours ouverts à la réservation négatif.")
            if record.booking_open_days_number > 180:
                raise ValidationError(
                    u"Vous ne pouvez pas avoir un nombre de jours ouverts à la réservation supérieur 180.")

    @api.depends('booking_company_dependent')
    def _compute_booking_terms_file(self):
        if not self.booking_company_dependent:
            self.booking_terms_file = self.website_id.company_id.of_booking_terms_file
            self.booking_terms_filename = self.website_id.company_id.of_booking_terms_filename
        else:
            self.booking_terms_file = self.env.user.company_id.of_booking_terms_file
            self.booking_terms_filename = self.env.user.company_id.of_booking_terms_filename

    def _inverse_booking_terms_file(self):
        if not self.booking_company_dependent:
            company_id = self.website_id.company_id
        else:
            company_id = self.env.user.company_id
        company_id.of_booking_terms_file = self.booking_terms_file

    def _inverse_booking_terms_filename(self):
        if not self.booking_company_dependent:
            company_id = self.website_id.company_id
        else:
            company_id = self.env.user.company_id
        company_id.of_booking_terms_filename = self.booking_terms_filename

    @api.onchange('booking_company_dependent')
    def _onchange_booking_company_dependent(self):
        company_id = self.booking_company_dependent and self.env.user.company_id.id
        ir_values_obj = self.with_context(from_config=True).env['ir.values']
        self.update({
            'booking_opened_day_ids': ir_values_obj.get_default(
                'of.intervention.settings', 'booking_opened_day_ids', company_id=company_id),
            'booking_employee_ids': ir_values_obj.env['ir.values'].get_default(
                'of.intervention.settings', 'booking_employee_ids', company_id=company_id),
            'booking_search_mode': ir_values_obj.env['ir.values'].get_default(
                'of.intervention.settings', 'booking_search_mode', company_id=company_id),
            'booking_search_type': ir_values_obj.env['ir.values'].get_default(
                'of.intervention.settings', 'booking_search_type', company_id=company_id),
            'booking_search_max_criteria': ir_values_obj.env['ir.values'].get_default(
                'of.intervention.settings', 'booking_search_max_criteria', company_id=company_id),
            'booking_open_days_number': ir_values_obj.env['ir.values'].get_default(
                'of.intervention.settings', 'booking_open_days_number', company_id=company_id),
            'booking_allow_empty_days': ir_values_obj.env['ir.values'].get_default(
                'of.intervention.settings', 'booking_allow_empty_days', company_id=company_id),
            'booking_intervention_state': ir_values_obj.env['ir.values'].get_default(
                'of.intervention.settings', 'booking_intervention_state', company_id=company_id),
            'booking_display_price': ir_values_obj.env['ir.values'].get_default(
                'of.intervention.settings', 'booking_display_price', company_id=company_id),
            'website_edit_days_limit': ir_values_obj.env['ir.values'].get_default(
                'of.intervention.settings', 'website_edit_days_limit', company_id=company_id),
            'booking_morning_hours_label': ir_values_obj.env['ir.values'].get_default(
                'of.intervention.settings', 'booking_morning_hours_label', company_id=company_id),
            'booking_afternoon_hours_label': ir_values_obj.env['ir.values'].get_default(
                'of.intervention.settings', 'booking_afternoon_hours_label', company_id=company_id),
            'booking_validation_note': ir_values_obj.env['ir.values'].get_default(
                'of.intervention.settings', 'booking_validation_note', company_id=company_id),
        })

    @api.multi
    def set_booking_company_dependent_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'booking_company_dependent', self.booking_company_dependent,
            company_id=self.env.user.company_id.id)

    @api.multi
    def set_booking_open_new_customer_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'booking_open_new_customer', self.booking_open_new_customer)

    @api.multi
    def set_booking_intervention_company_id_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'booking_intervention_company_id', self.booking_intervention_company_id.id)

    @api.multi
    def set_booking_use_partner_company_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'booking_use_partner_company', self.booking_use_partner_company)

    @api.multi
    def set_booking_opened_day_ids_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'booking_opened_day_ids', self.booking_opened_day_ids.ids,
            company_id=self.booking_company_dependent and self.env.user.company_id.id)

    @api.multi
    def set_booking_employee_ids_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'booking_employee_ids', self.booking_employee_ids.ids,
            company_id=self.booking_company_dependent and self.env.user.company_id.id)

    @api.multi
    def set_booking_search_mode_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'booking_search_mode', self.booking_search_mode,
            company_id=self.booking_company_dependent and self.env.user.company_id.id)

    @api.multi
    def set_booking_search_types_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'booking_search_type', self.booking_search_type,
            company_id=self.booking_company_dependent and self.env.user.company_id.id)

    @api.multi
    def set_booking_search_max_criteria_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'booking_search_max_criteria', self.booking_search_max_criteria,
            company_id=self.booking_company_dependent and self.env.user.company_id.id)

    @api.multi
    def set_booking_open_days_number_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'booking_open_days_number', self.booking_open_days_number,
            company_id=self.booking_company_dependent and self.env.user.company_id.id)

    @api.multi
    def set_booking_allow_empty_days_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'booking_allow_empty_days', self.booking_allow_empty_days,
            company_id=self.booking_company_dependent and self.env.user.company_id.id)

    @api.multi
    def set_booking_intervention_state_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'booking_intervention_state', self.booking_intervention_state,
            company_id=self.booking_company_dependent and self.env.user.company_id.id)

    @api.multi
    def set_booking_display_price_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'booking_display_price', self.booking_display_price,
            company_id=self.booking_company_dependent and self.env.user.company_id.id)

    @api.multi
    def set_website_edit_days_limit_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'website_edit_days_limit', self.website_edit_days_limit,
            company_id=self.booking_company_dependent and self.env.user.company_id.id)

    @api.multi
    def set_booking_morning_hours_label_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'booking_morning_hours_label', self.booking_morning_hours_label,
            company_id=self.booking_company_dependent and self.env.user.company_id.id)

    @api.multi
    def set_booking_afternoon_hours_label_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'booking_afternoon_hours_label', self.booking_afternoon_hours_label,
            company_id=self.booking_company_dependent and self.env.user.company_id.id)

    @api.multi
    def set_booking_validation_note_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'booking_validation_note', self.booking_validation_note,
            company_id=self.booking_company_dependent and self.env.user.company_id.id)

    @api.model
    def _fields_company_dependent(self):
        return [
            'booking_opened_day_ids',
            'booking_employee_ids',
            'booking_search_mode',
            'booking_search_type',
            'booking_search_max_criteria',
            'booking_open_days_number',
            'booking_allow_empty_days',
            'booking_intervention_state',
            'booking_display_price',
            'website_edit_days_limit',
            'booking_morning_hours_label',
            'booking_afternoon_hours_label',
            'booking_validation_note',
        ]


class IrValues(models.Model):
    _inherit = 'ir.values'

    @api.model
    def get_default(self, model, field_name, for_all_users=True, company_id=False, condition=False):
        if model == 'of.intervention.settings' and not self._context.get('from_config'):
            fields_to_verify = self.env[model]._fields_company_dependent()
            if field_name in fields_to_verify:
                company_used = self._context.get('force_company', self.env.user.company_id.id)
                company_dependent = super(IrValues, self).get_default(
                    model, 'booking_company_dependent', company_id=company_used)
                if company_dependent:
                    company_id = company_used
        return super(IrValues, self).get_default(model, field_name, for_all_users, company_id, condition)
