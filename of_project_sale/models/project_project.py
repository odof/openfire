# -*- coding: utf8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class ProjectProject(models.Model):
    _inherit = 'project.project'

    of_sale_tag_ids = fields.Many2many(comodel_name='crm.lead.tag', string=u"Étiquettes ventes")
