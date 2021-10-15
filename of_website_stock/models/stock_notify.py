# -*- coding: utf-8 -*-
from odoo import api, fields, SUPERUSER_ID, models, _


class OfWebsiteStockNotify(models.Model):
    _name = 'of.website.stock.notify'
    _rec_name = 'product_id'

    partner_id = fields.Many2one('res.partner', 'Name')
    product_id = fields.Many2one('product.template', 'Product')
    email = fields.Char('Email')
    status = fields.Selection([('draft', 'Draft'), ('done', 'Done')], string='Status', readonly=True, default='draft')

    @api.model
    def _cron_of_website_stock_notification(self):
        stock_notify_ids = self.search([('status', '=', 'draft')])
        super_user = self.env['res.users'].browse(SUPERUSER_ID)
        for stock_notify_id in stock_notify_ids:
            if stock_notify_id.product_id.qty_available > 0:
                template_id = self.env.ref('of_website_stock.email_template_sale_stock_notification')

                if template_id:
                    values = template_id.generate_email(stock_notify_id.id, fields=None)
                    values['email_from'] = super_user.email
                    values['email_to'] = stock_notify_id.email
                    values['res_id'] = False
                    mail_mail_obj = self.env['mail.mail']
                    msg_id = mail_mail_obj.create(values)
                    if msg_id:
                        mail_mail_obj.send([msg_id])

                    stock_notify_id.status = 'done'

        return True
