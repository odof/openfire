# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def message_post_xmlrpc(self, **kwargs):
        return self.message_post(**kwargs)
