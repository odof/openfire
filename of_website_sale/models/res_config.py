from odoo import fields, models


class WebsiteConfigSettings(models.TransientModel):
    _inherit = 'website.config.settings'

    of_pricelist_b2c_id = fields.Many2one(
        'product.pricelist', related='website_id.of_pricelist_b2c_id', string='Liste de prix B2C')
    of_pricelist_b2b_id = fields.Many2one(
        'product.pricelist', related='website_id.of_pricelist_b2b_id', string='Liste de prix B2B')
    of_fiscal_position_b2c_id = fields.Many2one(
        'account.fiscal.position', related='website_id.of_fiscal_position_b2c_id', string='Position fiscale B2C')
    of_fiscal_position_b2b_id = fields.Many2one(
        'account.fiscal.position', related='website_id.of_fiscal_position_b2b_id', string='Position fiscale B2B')


class Website(models.Model):
    _inherit = 'website'

    of_pricelist_b2c_id = fields.Many2one('product.pricelist', string='Liste de prix B2C')
    of_pricelist_b2b_id = fields.Many2one('product.pricelist', string='Liste de prix B2B')
    of_fiscal_position_b2c_id = fields.Many2one('account.fiscal.position', string='Position fiscale B2C')
    of_fiscal_position_b2b_id = fields.Many2one('account.fiscal.position', string='Position fiscale B2B')
