# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.depends('product_id', 'journal_id')
    def _compute_name(self):
        super()._compute_name()
        for line in self:
            if line.journal_id.type != 'sale':
                continue
            if not (line.product_id.of_standard_id.active and line.product_id.of_standard_id.display_docs):
                continue
            if line.partner_id.lang:
                product = line.product_id.with_context(lang=line.partner_id.lang)
            else:
                product = line.product_id
            if not product.of_description_standard:
                continue
            line.name = (
                line.name
                + "\n"
                + _("%s compliant: %s") % (product.of_standard_id.code, product.of_description_standard)
            )
