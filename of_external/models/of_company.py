# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class ResCompany(models.Model):
    _inherit = "res.company"
    use_of_custom_footer = fields.Boolean(string='use company custom footer',help='check if you want to use this custom footer for your pdf reports')
    of_custom_footer_line_1 = fields.Char(string='line 1')
    of_custom_footer_line_2 = fields.Char(string='line 2')
    of_custom_footer_line_1_size = fields.Selection([('medium', 'Medium'), ('small', 'Small'), ('smaller', 'Smaller'), ('x-small', 'X-Small')], string='Size', default='small', required=True)
    of_custom_footer_line_2_size = fields.Selection([('medium', 'Medium'), ('small', 'Small'), ('smaller', 'Smaller'), ('x-small', 'X-Small')], string='Size', default='small', required=True)
    
    
    