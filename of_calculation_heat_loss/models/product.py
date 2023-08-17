# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import re

from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    of_puissance_nom_flo = fields.Float(
        string=u"Puissance nominale (nombre flottant)", compute='_compute_of_puissance_nom_flo', store=True)

    @api.depends('of_puissance_nom')
    def _compute_of_puissance_nom_flo(self):
        for record in self:
            if record.of_puissance_nom:
                # Regular expression for extracting float value
                pattern = r"\d+[.,]?\d*"

                # extract float value
                match = re.search(pattern, record.of_puissance_nom)

                if match:
                    record.of_puissance_nom_flo = float(match.group().replace(",", "."))

