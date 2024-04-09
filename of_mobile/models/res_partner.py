# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def write(self, vals):
        res = super().write(vals)
        self.env['calendar.event'].action_update_date([('of_partner_id', '=', self.id)])
        return res

    def unlink(self):
        self.env['calendar.event'].action_update_date([('of_partner_id', '=', self.id)])
        return super().unlink()
