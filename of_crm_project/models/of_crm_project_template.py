# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFCRMProjectTemplate(models.Model):
    _name = 'of.crm.project.template'

    name = fields.Char(required=True, translate=True)
    attr_ids = fields.Many2many(
        'of.crm.project.attr',
        'crm_project_template_attr_rel',
        'template_id',
        'attr_id',
        string="Attributes",
        help=u"Liste des attributs de ce modèle. Ils seront copiés dans la fiche projet si ce modèle est sélectionné.",
    )
    active = fields.Boolean(default=True)
