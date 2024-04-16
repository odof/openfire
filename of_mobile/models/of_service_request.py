# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import _, api, fields, models


class OFServiceRequest(models.Model):
    _inherit = 'of.service.request'

    @api.model
    def _default_mobile(self):
        return self.env['ir.config_parameter'].sudo().get_param('of_mobile.auto_publish_service') or False

    mobile = fields.Boolean(string="Mobile Service Request", default=lambda s: s._default_mobile())

    def action_button_toggle_mobile(self):
        self.ensure_one()
        self.mobile = not self.mobile

    def action_mass_toggle_mobile(self):
        self.write({'mobile': True})
        return self.env['of.popup.wizard'].popup_return(message=_("%s SR were published on mobile") % len(self))
