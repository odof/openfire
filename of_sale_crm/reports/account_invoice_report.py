# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountInvoiceReport(models.Model):
    _inherit = 'account.invoice.report'

    of_canvasser_id = fields.Many2one(comodel_name='res.users', string="Prospecteur", readonly=True)
    of_partner_tags = fields.Char(string="Étiquettes du partenaire", readonly=True)

    def _select(self):
        res = super()._select()
        res += ", sub.of_prospecteur_id AS of_canvasser_id"
        res += ", sub.of_partner_tags AS of_partner_tags"
        return res

    def _sub_select(self):
        res = super()._sub_select()
        res += ", partner.of_prospecteur_id"
        res += """, (   SELECT  STRING_AGG(RPC.name, ' - ' ORDER BY RPC.name)
                                FROM    res_partner_res_partner_category_rel            RPRPCR
                                ,       res_partner_category                            RPC
                                WHERE   RPRPCR.partner_id                               = partner.id
                                AND     RPC.id                                          = RPRPCR.category_id
                            )  AS of_partner_tags"""
        return res

    def _group_by(self):
        res = super()._group_by()
        res += ", partner.of_prospecteur_id"
        res += ", partner.id"
        return res
