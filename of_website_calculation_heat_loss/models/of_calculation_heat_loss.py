# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import re

import requests

from odoo import api, fields, models


class OFCalculationHeatLoss(models.Model):
    _inherit = 'of.calculation.heat.loss'

    partner_firstname = fields.Char(string=u"Prénom", related='partner_id.firstname')
    partner_lastname = fields.Char(string=u"Nom", related='partner_id.lastname')
    pro_partner_id = fields.Many2one(comodel_name='res.partner', string=u"Partenaire Professionnel")
    pro_partner_name = fields.Char(string=u"Nom de l'entreprise", related='pro_partner_id.name')
    pro_partner_email = fields.Char(string=u"Email de l'entreprise", related='pro_partner_id.email')
    mailing_attempt = fields.Selection(
        selection=[
            ('no_attempt', u"Aucune tentative d'envoi"),
            ('failed', u"Échec d'envoi"),
            ('success', u"Envoi réussi"),
        ], string=u"Tentative d'envoi de mail", default='no_attempt'
    )

    @api.model
    def create(self, vals):
        if not vals.get('pro_partner_id'):
            vals, partner = self._of_extract_pro_partner_values(vals)  # split vals
            vals['pro_partner_id'] = partner and partner.id
        return super(OFCalculationHeatLoss, self).create(vals)

    def write(self, vals):
        if len(self) == 1 and not vals.get('pro_partner_id', self.pro_partner_id):
            vals, partner = self._of_extract_pro_partner_values(vals)  # split vals
            vals['pro_partner_id'] = partner and partner.id
        return super(OFCalculationHeatLoss, self).write(vals)

    @api.model
    def _of_extract_partner_values(self, vals):
        new_vals, partner_vals = super(OFCalculationHeatLoss, self)._of_extract_partner_values(vals)
        if any(field_name in partner_vals for field_name in ['firstname', 'lastname']) and 'name' in partner_vals:
            del partner_vals['name']
        return new_vals, partner_vals

    @api.model
    def get_altitude_ids_from_zip(self, zip):
        if not zip:
            return []
        department_obj = self.env['of.calculation.department']
        department = department_obj.search([('code', '=', zip[:2])], limit=1)
        if department:
            altitudes = department.base_temperature_id.line_ids.mapped('altitude_id')
            return altitudes.ids

    @api.model
    def _of_extract_pro_partner_values(self, vals):
        new_vals = vals.copy()
        partner_obj = self.env['res.partner']
        partner_vals = {}
        for field_name, val in vals.iteritems():
            if field_name not in self._fields:  # don't take vals that are not fields into account
                continue
            field = self._fields[field_name]
            # field is not related or is partner_name-> let it be
            if not getattr(field, 'related'):
                continue
            related = field.related
            if related and related[0] == 'pro_partner_id':  # field related to partner_id
                partner_vals['.'.join(related[1:])] = val  # add value to partner_vals
                del new_vals[field_name]  # take value out of new vals
        partner = False
        if partner_vals.get('email'):
            partner = partner_obj.search([('email', '=', partner_vals['email'])], limit=1)
        if not partner and partner_vals:
            partner_vals.update({
                'company_type': 'company',
            })
            partner = partner_obj.create(partner_vals)
        return new_vals, partner

    @api.multi
    def geolocalize(self):
        self.ensure_one()
        try:
            self.partner_id.geo_code()
        except Exception as e:
            return False
        elevation_api_url = 'https://api.open-elevation.com/api/v1/lookup'
        if (
            self.partner_id.geocoding in ('not_tried', 'no_address', 'failure') or
            self.partner_id.geocoding == 'need_verif' and
            self.partner_id.precision in ('no_address', 'unknown', 'not_tried', 'low')
        ):
            return
        try:
            req = requests.get(
                elevation_api_url, params={'locations': "%s,%s" % (self.partner_id.geo_lat, self.partner_id.geo_lng)}
            )
            result = req.json()
            if result:
                elevation = result['results'][0]['elevation']
            else:
                return
        except:
            return
        department_obj = self.env['of.calculation.department']
        department = department_obj.search([('code', '=', self.partner_id.zip[:2])], limit=1)
        if department:
            altitudes = department.base_temperature_id.line_ids.mapped('altitude_id')
            if altitudes:
                for altitude in altitudes:
                    values = re.findall(r'\d+', altitude.name)
                    if values and float(values[0]) <= elevation < float(values[-1]):
                        break
                else:
                    return False
                self.write({'altitude_id': altitude.id})
