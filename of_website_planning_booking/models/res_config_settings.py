# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import api, models, fields
from odoo.exceptions import ValidationError


class OFInterventionSettings(models.TransientModel):
    _inherit = 'of.intervention.settings'

    @api.model
    def _auto_init(self):
        super(OFInterventionSettings, self)._auto_init()
        if self.env['ir.values'].get_default('of.intervention.settings', 'website_booking_allowed_month_ids') is None:
            self.env['ir.values'].set_default(
                'of.intervention.settings', 'website_booking_allowed_month_ids', self._default_allowed_month_ids())
        if self.env['ir.values'].get_default('of.intervention.settings', 'website_booking_allowed_day_ids') is None:
            self.env['ir.values'].set_default(
                'of.intervention.settings', 'website_booking_allowed_day_ids', self._default_allowed_day_ids())
        if self.env['ir.values'].get_default('of.intervention.settings', 'website_booking_open_days_number') is None:
            self.env['ir.values'].set_default('of.intervention.settings', 'website_booking_open_days_number', 60)
        if self.env['ir.values'].get_default('of.intervention.settings', 'website_booking_allow_empty_days') is None:
            self.env['ir.values'].set_default('of.intervention.settings', 'website_booking_allow_empty_days', True)
        if self.env['ir.values'].get_default('of.intervention.settings', 'website_booking_slot_size') is None:
            self.env['ir.values'].set_default('of.intervention.settings', 'website_booking_slot_size', 'half_day')
        if self.env['ir.values'].get_default('of.intervention.settings', 'website_booking_intervention_state') is None:
            self.env['ir.values'].set_default('of.intervention.settings', 'website_booking_intervention_state', 'draft')

    def _default_website(self):
        return self.env['website'].search([], limit=1)

    def _default_allowed_month_ids(self):
        months = self.env['of.mois'].search([], order='numero')
        res = [month.id for month in months]
        return res

    def _default_allowed_day_ids(self):
        days = self.env['of.jours'].search([('numero', '<', 6)], order='numero')
        res = [day.id for day in days]
        return res

    website_booking_allowed_month_ids = fields.Many2many(
        comodel_name='of.mois', string=u"(OF) Mois ouverts", default=_default_allowed_month_ids)
    website_booking_allowed_day_ids = fields.Many2many(
        comodel_name='of.jours', string=u"(OF) Jours ouverts", default=_default_allowed_day_ids)
    website_booking_allowed_employee_ids = fields.Many2many(
        comodel_name='hr.employee', relation='of_intervention_settings_web_allowed_employee_rel',
        column1='of_intervention_settings_id', column2='employee_id', string=u"(OF) Techniciens disponibles",
        domain=[('of_est_intervenant', '=', True)])
    website_booking_open_days_number = fields.Integer(
        string=u"(OF) Nombre de jours ouverts à la réservation (max 180 jours)", default=60)
    website_booking_allow_empty_days = fields.Boolean(
        string=u"(OF) Autorise la réservation de créneau sur des journées vierges", default=True)
    website_booking_intervention_state = fields.Selection(selection=[
        ('draft', u"Brouillon"),
        ('confirm', u"Confirmé")
        ], string=u"(OF) État des RDV à la prise de RDV en ligne", default='draft', required=True)
    website_booking_tache_price = fields.Boolean(string=u"(OF) Afficher le prix de la prestation")
    website_booking_slot_size = fields.Selection(
        selection=[('half_day', u"Demi-journée"), ('manual', u"Manuelle")], string=u"(OF) Granularité de réservation", default='half_day',
        required=True)
    group_website_booking_allow_park_creation = fields.Boolean(
        string=u"(OF) Création de parcs",
        implied_group='of_website_planning_booking.group_website_booking_allow_park_creation',
        group='base.group_portal,base.group_user,base.group_public',
        help=u"Autorise la création des parcs installés extérieurs")
    group_website_booking_allow_park_brand_creation = fields.Boolean(
        string=u"(OF) Ajout de marques",
        implied_group='of_website_planning_booking.group_website_booking_allow_park_brand_creation',
        group='base.group_portal,base.group_user,base.group_public',
        help=u"Autorise la création des parcs installés sur des marques extérieures")
    website_booking_default_product_brand_id = fields.Many2one(
        comodel_name='of.product.brand', string=u"(OF) Marque des parcs",
        help=u"Marque utilisée pour la création des parcs installés",
        default=lambda self: self.env['ir.model.data'].xmlid_to_object(
            'of_website_planning_booking.of_website_planning_booking_brand_default'))
    website_id = fields.Many2one(comodel_name='website', string=u"Site web", default=_default_website, required=True)
    website_booking_terms_file = fields.Binary(
        string=u"(OF) Fichier PDF des Conditions Générales de Vente",
        filename='website_booking_terms_filename',
        compute='_compute_website_booking_terms_file',
        inverse='_inverse_website_booking_terms_file')
    website_booking_terms_filename = fields.Char(
        string=u"(OF) Nom du fichier PDF des Conditions Générales de Vente",
        compute='_compute_website_booking_terms_file',
        inverse='_inverse_website_booking_terms_filename')
    website_edit_days_limit = fields.Integer(
        string=u"(OF) Limite de modifications")
    website_booking_company_dependent = fields.Boolean(
        string=u"(OF) Définir une configuration spécifique à cette société")

    @api.depends('website_booking_company_dependent')
    def _compute_website_booking_terms_file(self):
        if not self.website_booking_company_dependent:
            self.website_booking_terms_file = self.website_id.company_id.of_website_booking_terms_file
            self.website_booking_terms_filename = self.website_id.company_id.of_website_booking_terms_filename
        else:
            self.website_booking_terms_file = self.env.user.company_id.of_website_booking_terms_file
            self.website_booking_terms_filename = self.env.user.company_id.of_website_booking_terms_filename

    def _inverse_website_booking_terms_file(self):
        if not self.website_booking_company_dependent:
            company_id = self.website_id.company_id
        else:
            company_id = self.env.user.company_id
        company_id.of_website_booking_terms_file = self.website_booking_terms_file

    def _inverse_website_booking_terms_filename(self):
        if not self.website_booking_company_dependent:
            company_id = self.website_id.company_id
        else:
            company_id = self.env.user.company_id
        company_id.of_website_booking_terms_filename = self.website_booking_terms_filename


    @api.constrains('website_booking_open_days_number')
    def _check_website_booking_open_days_number_constaint(self):
        for record in self:
            if record.website_booking_open_days_number < 0:
                raise ValidationError(u"Vous ne pouvez pas avoir un nombre de jours ouverts à la réservation négatif.")
            if record.website_booking_open_days_number > 180:
                raise ValidationError(u"Vous ne pouvez pas avoir un nombre de jours ouverts à la réservation supérieur "
                                      u"à 180.")

    @api.multi
    def set_website_booking_allowed_month_ids_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'website_booking_allowed_month_ids', self.website_booking_allowed_month_ids.ids,
            company_id=self.website_booking_company_dependent and self.company_id.id)

    @api.multi
    def set_website_booking_allowed_day_ids_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'website_booking_allowed_day_ids', self.website_booking_allowed_day_ids.ids,
            company_id=self.website_booking_company_dependent and self.company_id.id)

    @api.multi
    def set_website_booking_allowed_employee_ids_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'website_booking_allowed_employee_ids',
            self.website_booking_allowed_employee_ids.ids,
            company_id=self.website_booking_company_dependent and self.company_id.id)

    @api.multi
    def set_website_booking_open_days_number_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'website_booking_open_days_number', self.website_booking_open_days_number,
            company_id=self.website_booking_company_dependent and self.company_id.id)

    @api.multi
    def set_website_booking_allow_empty_days_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'website_booking_allow_empty_days', self.website_booking_allow_empty_days,
            company_id=self.website_booking_company_dependent and self.company_id.id)

    @api.multi
    def set_website_booking_intervention_state_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'website_booking_intervention_state', self.website_booking_intervention_state,
            company_id=self.website_booking_company_dependent and self.company_id.id)

    @api.multi
    def set_website_booking_tache_price_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'website_booking_tache_price', self.website_booking_tache_price,
            company_id=self.website_booking_company_dependent and self.company_id.id)

    @api.multi
    def set_website_booking_slot_size_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'website_booking_slot_size', self.website_booking_slot_size,
            company_id=self.website_booking_company_dependent and self.company_id.id)

    @api.multi
    def set_website_booking_default_product_brand_id_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'website_booking_default_product_brand_id',
            self.website_booking_default_product_brand_id.id,
            company_id=self.website_booking_company_dependent and self.company_id.id)

    @api.multi
    def set_website_edit_days_limit_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'website_edit_days_limit',
            self.website_edit_days_limit,
            company_id=self.website_edit_days_limit and self.company_id.id)

    @api.multi
    def set_website_booking_company_dependent_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'website_booking_company_dependent',
            self.website_booking_company_dependent,
            company_id=self.company_id.id)

    @api.onchange('group_website_booking_allow_park_creation')
    def _onchange_group_website_booking_allow_park_creation(self):
        self.ensure_one()
        if not self.group_website_booking_allow_park_creation:
            self.group_website_booking_allow_park_brand_creation = False

    @api.onchange('website_booking_company_dependent')
    def _onchange_website_booking_company_dependent(self):
        cd = self.website_booking_company_dependent  # cd = company_dependent
        ir_values_obj = self.with_context(from_config=True).env['ir.values']
        self.update({
            'website_booking_allowed_month_ids': ir_values_obj.get_default(
            'of.intervention.settings', 'website_booking_allowed_month_ids', company_id=cd and self.company_id.id),
            'website_booking_allowed_day_ids': ir_values_obj.env['ir.values'].get_default(
            'of.intervention.settings', 'website_booking_allowed_day_ids', company_id=cd and self.company_id.id),
            'website_booking_allowed_employee_ids': ir_values_obj.env['ir.values'].get_default(
            'of.intervention.settings', 'website_booking_allowed_employee_ids', company_id=cd and self.company_id.id),
            'website_booking_open_days_number': ir_values_obj.env['ir.values'].get_default(
            'of.intervention.settings', 'website_booking_open_days_number', company_id=cd and self.company_id.id),
            'website_booking_allow_empty_days': ir_values_obj.env['ir.values'].get_default(
            'of.intervention.settings', 'website_booking_allow_empty_days', company_id=cd and self.company_id.id),
            'website_booking_intervention_state': ir_values_obj.env['ir.values'].get_default(
            'of.intervention.settings', 'website_booking_intervention_state', company_id=cd and self.company_id.id),
            'website_booking_tache_price': ir_values_obj.env['ir.values'].get_default(
            'of.intervention.settings', 'website_booking_tache_price', company_id=cd and self.company_id.id),
            'website_booking_slot_size': ir_values_obj.env['ir.values'].get_default(
            'of.intervention.settings', 'website_booking_slot_size', company_id=cd and self.company_id.id),
            'website_booking_default_product_brand_id': ir_values_obj.env['ir.values'].get_default(
            'of.intervention.settings', 'website_booking_default_product_brand_id', company_id=cd and self.company_id.id),
            'website_edit_days_limit': ir_values_obj.env['ir.values'].get_default(
            'of.intervention.settings', 'website_edit_days_limit', company_id=cd and self.company_id.id),
        })

    @api.model
    def _fields_company_dependent_potential(self):
        return [
            'website_booking_allowed_month_ids',
            'website_booking_allowed_day_ids',
            'website_booking_allowed_employee_ids',
            'website_booking_open_days_number',
            'website_booking_allow_empty_days',
            'website_booking_intervention_state',
            'website_booking_tache_price',
            'website_booking_slot_size',
            'website_booking_default_product_brand_id',
            'website_edit_days_limit',
        ]


class IrValues(models.Model):
    _inherit = 'ir.values'

    @api.model
    def get_default(self, model, field_name, for_all_users=True, company_id=False, condition=False):
        if model == 'of.intervention.settings' and not self._context.get('from_config'):
            fields_to_verify = self.env[model]._fields_company_dependent_potential()
            if field_name in fields_to_verify:
                company_used = self._context.get('force_company', self.env.user.company_id.id)
                company_dependent = super(IrValues, self).get_default(
                    model, 'website_booking_company_dependent', company_id=company_used)
                if company_dependent:
                    company_id = company_used
        return super(IrValues, self).get_default(model, field_name, for_all_users, company_id, condition)

