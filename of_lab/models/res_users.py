# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api, fields


class ResUsers(models.Model):
    _inherit = 'res.users'

    of_portal = fields.Boolean(
        compute='_compute_of_portal', compute_sudo=True, string=u"utilisateur portail", store=True)

    @api.depends('groups_id')
    def _compute_of_portal(self):
        for user in self:
            user.of_portal = user.has_group('base.group_portal')

    @api.model
    def _init_template_user(self):
        # Add group_user on template user in order to be able to create an internal user from portal
        template_user = self.env.ref('auth_signup.default_template_user')
        template_user.write({'groups_id': [(4, self.env.ref('base.group_user').id),
                                           (4, self.env.ref('sales_team.group_sale_salesman').id),
                                           (4, self.env.ref('of_planning.group_planning_intervention_responsible').id),
                                           (4, self.env.ref('purchase.group_purchase_user').id)],
                             'action_id': self.env.ref('of_lab.action_open_lab').id,
                             'tz': "Europe/Paris"})
        # Activate auth signup options
        self.env['ir.config_parameter'].set_param('auth_signup.reset_password', True)
        self.env['ir.config_parameter'].set_param('auth_signup.allow_uninvited', True)

    @api.model
    def _signup_create_user(self, values):
        user = super(ResUsers, self)._signup_create_user(values)

        # Partner address
        user.partner_id.write({
            'street': u"Boulevard de l'Europe",
            'street2': u"EUREXPO",
            'zip': u"69680",
            'city': u"Chassieu",
        })

        # Test partner firstname
        if not user.partner_id.firstname:
            user.partner_id.firstname = u"OpenFire"

        # Employee creation
        week_days = self.env['of.jours'].search([('numero', '<', 6)])

        slots = []
        for day in week_days:
            for start_hour, end_hour in ((8, 14), (14, 20)):
                slot = self.env['of.horaire.creneau'].search(
                    [('jour_id', '=', day.id), ('heure_debut', '=', start_hour), ('heure_fin', '=', end_hour)], limit=1)
                if not slot:
                    slot = self.env['of.horaire.creneau'].create({
                        'jour_id': day.id,
                        'heure_debut': start_hour,
                        'heure_fin': end_hour,
                    })
                slots.append((4, slot.id))

        self.env['hr.employee'].create({
            'name': user.name,
            'user_id': user.id,
            'of_est_intervenant': True,
            'of_est_commercial': True,
            'of_toutes_taches': True,
            'of_segment_ids': [
                (0, 0, {
                    'date_deb': '1970-01-01',
                    'date_fin': False,
                    'permanent': True,
                    'creneau_ids': slots
                })
            ]
        })

        # Parc creation
        parc = self.env['of.parc.installe'].new({
            'name': u"%s - Mon appareil" % user.partner_id.name,
            'client_id': user.partner_id.id,
            'product_id': self.env.ref('of_lab.of_lab_fire_device').product_variant_ids[0].id,
        })
        parc.onchange_product_id()
        parc._onchange_client_id()
        parc_vals = parc._convert_to_write(parc._cache)
        self.env['of.parc.installe'].create(parc_vals)

        # Sale order creation
        order = self.env['sale.order'].new({
            'partner_id': user.partner_id.id,
            'of_template_id': self.env.ref('of_lab.of_lab_sale_quote_template').id,
        })
        order.onchange_partner_id()
        order.onchange_template_id()
        order_vals = order._convert_to_write(order._cache)
        self.env['sale.order'].create(order_vals)

        return user


class ResPartner(models.Model):
    _inherit = 'res.partner'

    of_portal = fields.Boolean(
        compute='_compute_of_portal', compute_sudo=True, string=u"Partenaire portail", store=True)

    @api.depends('user_ids.of_portal')
    def _compute_of_portal(self):
        for partner in self:
            partner.of_portal = any(user.of_portal for user in partner.user_ids)
