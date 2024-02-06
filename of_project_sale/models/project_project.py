# -*- coding: utf8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class ProjectProject(models.Model):
    _inherit = 'project.project'

    of_sale_tag_ids = fields.Many2many(comodel_name='crm.lead.tag', string=u"Étiquettes ventes")

    @api.onchange('of_sale_id')
    def _onchange_of_sale_id(self):
        res = super(ProjectProject, self)._onchange_of_sale_id()
        if self.of_sale_id and self.of_sale_id.tag_ids:
            self.of_sale_tag_ids = [(6, 0, self.of_sale_id.tag_ids.ids)]
        return res
