# -*- coding: utf-8 -*-

from odoo import api, models, fields

class OFMapViewMixin(models.AbstractModel):
    _name = "of.map.view.mixin"

    @api.model
    def get_color_map(self):
        raise NotImplementedError("A class inheriting from this one must implement a 'get_color_map' function")


class ResPartner(models.Model):
    _name = "res.partner"
    _inherit = ["res.partner","of.map.view.mixin"]

    partner_map_ids = fields.One2many('res.partner', compute="_compute_partner_map_ids")
    # Couleur de contrôle
    color_parent_enfant = fields.Char(compute='_compute_color_parent_enfant', string='Couleur', store=False)

    @api.multi
    @api.depends('parent_id', 'child_ids')
    def _compute_partner_map_ids(self):
        # One2many pour afficher la vue map
        for partner in self:
            partner_ids = []
            if isinstance(partner.id, (int, long)):
                if partner.parent_id and partner.parent_id.geo_lat != 0:
                    partner_ids.append(partner.parent_id.id)
                if partner.geo_lat != 0:
                    partner_ids.append(partner.id)
                if partner.child_ids:
                    partner_ids += [child.id for child in partner.child_ids if child.geo_lat != 0]
            partner.partner_map_ids = [(6, 0, partner_ids)]

    @api.multi
    @api.depends('parent_id', 'child_ids')
    def _compute_color_parent_enfant(self):
        u""" COULEURS :
        Vert : parent
        Bleu : partenaire
        Noir : enfants
        """
        active_partner_id = self._context.get('active_partner_id')
        if active_partner_id:
            for partner in self:
                if partner.child_ids and active_partner_id in partner.child_ids.ids:  # est le parent
                    partner.color_parent_enfant = 'green'
                elif partner.parent_id and partner.parent_id.id == active_partner_id:  # est un enfant
                    partner.color_parent_enfant = 'black'
                elif partner.id == active_partner_id:  # est le partenaire
                    partner.color_parent_enfant = 'blue'
        else:
            for partner in self:
                partner.color_parent_enfant = False

    @api.model
    def get_color_map(self):
        u"""
        fonction pour la légende de la vue map
        """
        if self._context.get('parent_enfant'):
            title = ""
            v0 = {'label': "le partenaire", 'value': 'blue'}
            v1 = {'label': u'son parent', 'value': 'black'}
            v2 = {'label': u'ses enfants', 'value': 'green'}
            return {"title": title, "values": (v0, v1, v2)}
        return None
