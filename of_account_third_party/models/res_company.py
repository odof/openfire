# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    of_customer_code = fields.Char(string="Customer code", default="('411%05i' % partner.id, partner.name)")
    of_supplier_code = fields.Char(string="Supplier code", default="('401%05i' % partner.id, partner.name)")
