# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import api, models

logger = logging.getLogger(__name__)


class AccountFiscalPosition(models.Model):
    _inherit = 'account.fiscal.position'

    @api.model
    def _prepare_graphql_domain(self, select, domain):
        odoo_domain = super()._prepare_graphql_domain(select, domain)

        if select:
            if select.tax_type_use:
                # on va chercher le tuple qui doit être remplacé
                odoo_domain.remove(('tax_ids.tax_src_id.type_tax_use', '=', select.tax_type_use.value))
                odoo_domain += [
                    '|',
                    ('tax_ids.tax_src_id.type_tax_use', '=', select.tax_type_use.value),
                    ('of_default_tax_ids.type_tax_use', '=', select.tax_type_use.value),
                ]

        return odoo_domain
