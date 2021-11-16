# -*- coding: utf-8 -*-
from odoo import fields, models, api, _


# class ResCompany(models.Model):
#     _inherit = 'res.company'
#
#     of_website_security_lead = fields.Float('Website Safety Days', required=True, default = 0.0,
#         help="Margin of error for dates promised to customers on website.")


class Website(models.Model):
    _inherit = 'website'

    of_website_security_lead = fields.Integer('Website Safety Days', required=True, default=0)

    def get_website_config(self):
        return self.env['ir.values'].get_default('website.config.settings', 'of_stock_type')

    def get_of_unavailability_management(self):
        return self.env['ir.values'].get_default('website.config.settings', 'of_unavailability_management')

    def get_of_delivery_management(self):
        return self.env['ir.values'].get_default('website.config.settings', 'of_delivery_management')

    def get_of_website_security_lead(self):
        return self.of_website_security_lead or 0


class WebsiteConfigSettings(models.TransientModel):
    _inherit = 'website.config.settings'

    @api.model
    def _auto_init(self):
        """
        Cette fonction est appelée à chaque mise à jour mais ne fait quelque chose
        que la première fois qu'elle est appelée.
        """
        super(WebsiteConfigSettings, self)._auto_init()
        if not self.env['ir.values'].get_default('website.config.settings', 'of_stock_type'):
            self.env['ir.values'].sudo().set_default('website.config.settings', 'of_stock_type', 'none')
        if not self.env['ir.values'].get_default('website.config.settings', 'of_unavailability_management'):
            self.env['ir.values'].sudo()\
                .set_default('website.config.settings', 'of_unavailability_management', 'notify')
        if not self.env['ir.values'].get_default('website.config.settings', 'of_delivery_management'):
            self.env['ir.values'].sudo().set_default('website.config.settings', 'of_delivery_management', False)

    of_stock_type = fields.Selection([
        ('none', 'Display nothing'), ('on_hand', 'Qty On Hand'), ('forecast', 'Qty Forecast')], default='none',
        string=u"(OF) Stock Type to Display", help=u"Display Different stock type in Website.")
    of_unavailability_management = fields.Selection([
        ('notify', 'Mail notification on restock'), ('delay', 'Sell with a reception delay')], default='notify',
        string=u"(OF) Unavailability Management", help=u"How to handle unavailability")
    of_delivery_management = fields.Boolean(
        default=False, string=u"(OF) Delivery Management", help=u"Let the customer choose his delivery date")
    of_website_security_lead = fields.Integer(
        related='website_id.of_website_security_lead', string=u"(OF) Website Safety Days *",
        help=u"Margin of error for dates promised to customers on website.")

    @api.multi
    def set_of_stock_type_defaults(self):
        return self.env['ir.values'].sudo().set_default('website.config.settings', 'of_stock_type', self.of_stock_type)

    @api.multi
    def set_of_unavailability_management_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'website.config.settings', 'of_unavailability_management', self.of_unavailability_management)

    @api.multi
    def set_of_delivery_management_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'website.config.settings', 'of_delivery_management', self.of_delivery_management)
