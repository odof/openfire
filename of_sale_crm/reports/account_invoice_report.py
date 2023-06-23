# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountInvoiceReport(models.Model):
    _inherit = 'account.invoice.report'

    of_canvasser_id = fields.Many2one(comodel_name='res.users', string="Canvasser", readonly=True)
    of_partner_tags = fields.Char(string="Partner Tags")

    @api.model
    def _select(self):
        res = super()._select()
        res += ", move.of_canvasser_id"
        res += (
            """, (
            SELECT STRING_AGG(COALESCE(RPC.name->>'%s', RPC.name->>'en_US'), ' - ' ORDER BY RPC.name)
                FROM
                    res_partner_res_partner_category_rel RPRPCR,
                    res_partner_category RPC
                WHERE
                    RPRPCR.partner_id = partner.id
                    AND RPC.id = RPRPCR.category_id
            )  AS of_partner_tags"""  # nosec B608: we trust env.user.lang
            % self.env.user.lang
        )
        return res

    def _group_by(self):
        res = super()._group_by()
        res += ", partner.of_canvasser_id"
        res += ", partner.id"
        res += ", partner.of_partner_tags"
        return res
