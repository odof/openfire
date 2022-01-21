# -*- encoding: utf-8 -*-

from odoo import api, models, fields


class ResPartner(models.Model):
    _inherit = "res.partner"

    service_address_ids = fields.One2many(
        'of.service', 'address_id', string=u"Demandes d'intervention", context={'active_test': False})
    service_partner_ids = fields.One2many(
        'of.service', 'partner_id', string=u"Demandes d'intervention du partenaire", context={'active_test': False},
        help=u"Demandes d'intervention liées au partenaire, incluant les demandes des contacts associés")
    a_programmer_ids = fields.Many2many('of.service', string=u"DI à programmer", compute="compute_a_programmer")
    a_programmer_count = fields.Integer(string=u'Nombre DI à programmer', compute='compute_a_programmer')
    recurrent_ids = fields.Many2many('of.service', string=u"DI récurrentes", compute="compute_a_programmer")
    recurrent_count = fields.Integer(string=u'Nombre DI récurrentes', compute='compute_a_programmer')

    # @api.depends

    @api.multi
    def compute_a_programmer(self):
        service_obj = self.env['of.service']
        for partner in self:
            service_ids = service_obj.search([
                '|',
                ('partner_id', 'child_of', partner.id),
                ('address_id', 'child_of', partner.id),
            ])
            partner.a_programmer_ids = service_ids.filtered(
                lambda s: s.state in ('draft', 'to_plan', 'part_planned', 'late'))
            partner.a_programmer_count = len(partner.a_programmer_ids)
            partner.recurrent_ids = service_ids.filtered(
                lambda s: s.recurrence and s.state not in ('draft', 'done', 'cancel'))
            partner.recurrent_count = len(partner.recurrent_ids)

    # Actions

    @api.multi
    def action_prevoir_intervention(self):
        self.ensure_one()
        action = self.env.ref('of_service.action_of_service_prog_form_planning').read()[0]
        action['name'] = u"Prévoir une intervention"
        action['view_mode'] = "form"
        action['view_ids'] = False
        action['view_id'] = self.env['ir.model.data'].xmlid_to_res_id("of_service.view_of_service_form")
        action['views'] = False
        action['target'] = "new"
        action['context'] = {
            'default_partner_id': self.id,
            'default_address_id': self.address_get(adr_pref=['delivery']) or self.id,
            'default_recurrence': False,
            'default_date_next': fields.Date.today(),
            'default_origin': u"[Partenaire] " + self.name,
            'hide_bouton_planif': True,
            'default_type_id': self.env.ref('of_service.of_service_type_maintenance').id,
        }
        return action

    @api.multi
    def action_view_a_programmer(self):
        action = self.env.ref('of_service.action_of_service_prog_form_planning').read()[0]

        if len(self._ids) == 1:
            action['context'] = str(self._get_action_view_a_programmer_context())

        action['domain'] = [
            '|',
            ('partner_id', 'child_of', self.ids),
            ('address_id', 'child_of', self.ids),
        ]

        return action

    @api.multi
    def action_view_recurrent(self):
        action = self.env.ref('of_service.action_of_service_prog_form_planning').read()[0]

        if len(self._ids) == 1:
            action['context'] = str(self._get_action_view_recurrent_context())

        action['domain'] = [
            '|',
            ('partner_id', 'child_of', self.ids),
            ('address_id', 'child_of', self.ids),
            ('recurrence', '=', True),
        ]

        return action

    # Autres

    @api.multi
    def _get_action_view_a_programmer_context(self, context=None):
        if context is None:
            context = {}
        context.update({
            'default_partner_id': self.id,
            'default_address_id': self.address_get(adr_pref=['delivery']) or self.id,
            'default_recurrence': False,
            'default_date_next': fields.Date.today(),
            'default_origin': u"[Partenaire] " + self.name,
            'search_default_filter_draft': True,
            'search_default_filter_to_plan': True,
            'search_default_filter_part_planned': True,
            'search_default_filter_late': True,
            'hide_bouton_planif': True,
        })
        return context

    @api.multi
    def _get_action_view_recurrent_context(self, context=None):
        if context is None:
            context = {}
        context.update({
            'default_partner_id': self.id,
            'default_address_id': self.address_get(adr_pref=['delivery']) or self.id,
            'default_recurrence': True,
            'default_date_next': fields.Date.today(),
            'default_origin': u"[Partenaire] " + self.name,
            'search_default_filter_to_plan': True,
            'search_default_filter_planned': True,
            'search_default_filter_planned_soone': True,
            'search_default_filter_late': True,
            'search_default_filter_progress': True,
            'hide_bouton_planif': True,
        })
        return context
