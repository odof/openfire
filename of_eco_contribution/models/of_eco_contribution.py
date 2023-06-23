# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models, fields, _
from odoo.exceptions import ValidationError


class OFEcoOrganism(models.Model):
    _name = 'of.eco.organism'

    name = fields.Char(string=u"Nom de l'Éco-organisme", required=True)
    active = fields.Boolean(string=u"Actif", default=True)
    account_id = fields.Many2one(comodel_name='account.account', string=u"Compte comptable")
    contribution_ids = fields.One2many(
        comodel_name='of.eco.contribution', inverse_name='organism_id', string=u"Éco-contributions")


class OFEcoContribution(models.Model):
    _name = 'of.eco.contribution'

    name = fields.Char(string=u"Nom de l'Éco-contribution", compute='_compute_name', store=True)
    active = fields.Boolean(string=u"Actif", default=True)
    organism_id = fields.Many2one(comodel_name='of.eco.organism', string=u"Éco-organisme", required=True)
    code = fields.Char(string=u"Code éco-organism", required=True)
    description = fields.Text(string=u"Description")
    type = fields.Selection(selection=[
        ('unit', u"€/unité"),
        ('ton', u"€/tonne"),
        ('square_meter', u"€/m²"),
        ('cubic_meter', u"€/m³"),
        ('linear_meter', u"€/ml"),
    ],string=u"Type de tarif", required=True)
    price = fields.Float(string=u"Tarif", required=True)

    @api.constrains('code', 'organism_id')
    def _check_code_organism_no_duplicate(self):
        for record in self:
            if self.search_count([('code', '=', record.code), ('organism_id', '=', record.organism_id.id),
                                  ('id', '!=', record.id)]):
                raise ValidationError(u"Une Éco-contribution avec le même code existe déjà pour l'éco-organisme %s" \
                                      % record.organism_id.name)


    @api.depends('code', 'description', 'type', 'price')
    def _compute_name(self):
        selection = {key: val for key, val in self._fields['type'].selection}
        for record in self:
            base_name = " - ".join([text for text in (record.code, record.description) if text])
            price = "".join([text for text in (str(record.price), record.type and selection[record.type]) if text])
            record.name = "%s - %s" % (base_name, price)

    @api.model
    def create(self, vals):
        # dans le cas d'un import
        if self._context.get('import_file', False) and 'code' in vals and 'organism_id' in vals:
            found = self.search([('code', '=', vals['code']), ('organism_id', '=', vals['organism_id'])])
            # si il existe, on met a jour
            if found:
                found.write(vals)
                return found
        return super(OFEcoContribution, self).create(vals)
