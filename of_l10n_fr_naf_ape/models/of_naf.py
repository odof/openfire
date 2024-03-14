# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class OFNaf(models.Model):
    _name = 'of.naf'
    _description = u"Nomenclature d'activités française (NAF)"
    _order = 'parent_left, name'
    _parent_store = True
    _parent_order = 'name'

    name = fields.Char(string=u"Libellé", required=True)
    parent_id = fields.Many2one(comodel_name='of.naf', string=u"Catégorie mère", index=True, ondelete='cascade')
    child_ids = fields.One2many(comodel_name='of.naf', inverse_name='parent_id', string=u"Catégories filles")
    active = fields.Boolean(
        string=u"Actif", default=True, help=u"Décochez le champ 'Actif' pour cacher la catégorie sans la supprimer.")
    parent_left = fields.Integer(string=u"Parent gauche", index=True)
    parent_right = fields.Integer(string=u"Parent droit", index=True)
    partner_ids = fields.Many2many(
        comodel_name='res.partner', column1='naf_id', column2='partner_id', string=u"Partenaires")

    @api.constrains('parent_id')
    def _check_parent_id(self):
        if not self._check_recursion():
            raise ValidationError(u"Erreur ! On ne peut pas créer de catégories récursives.")

    @api.multi
    def name_get(self):
        if self._context.get('of_ape_display') == 'short':
            return super(OFNaf, self).name_get()

        res = []
        for category in self:
            names = []
            current = category
            while current:
                names.append(current.name)
                current = current.parent_id
            res.append((category.id, ' / '.join(reversed(names))))
        return res

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        if name:
            # Be sure name_search is symetric to name_get
            name = name.split(' / ')[-1]
            args = [('name', operator, name)] + args
        results = self.search(args, limit=limit).name_get()
        """When no results are found, try again with an additional "."."""
        if not results and name and len(name) > 2:
            # Add a "." after the 2nd character, in case that makes a NACE code
            results = super(OFNaf, self).name_search(
                '%s.%s' % (name[:2], name[2:]), args=args, operator=operator,
                limit=limit)
        return results
