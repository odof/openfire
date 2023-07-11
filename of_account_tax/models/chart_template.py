# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, models


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    def _get_fp_vals(self, company, position):
        val = super()._get_fp_vals(company, position)
        if tax_template_ref := self._context.get('tax_template_ref'):
            val.update(
                {'of_default_tax_ids': [Command.set([tax_template_ref[t].id for t in position.of_default_tax_ids])]}
            )
        return val
