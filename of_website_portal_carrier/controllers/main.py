# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.addons.website_portal.controllers.main import website_account


class WebsiteAccount(website_account):

    def _prepare_portal_layout_values(self):
        values = super(WebsiteAccount, self)._prepare_portal_layout_values()
        receipt_ids = request.env['stock.picking'].search([
            ('picking_type_id.warehouse_id.partner_id', '=', request.env.user.partner_id.id),
            ('state', 'not in', ('draft', 'cancel', 'done')),
            ('picking_type_id.code', '=', 'incoming'),
            ('min_date', '>', (datetime.today() - relativedelta(months=6)).strftime(DEFAULT_SERVER_DATE_FORMAT)),
            ('min_date', '<', (datetime.today() + relativedelta(months=6)).strftime(DEFAULT_SERVER_DATE_FORMAT)),
        ])
        values.update({
            'receipt_count': len(receipt_ids),
        })
        return values
    @http.route(['/my/receipts'], type='http', auth='user', website=True)
    def portal_my_receipts(self):
        values = self._prepare_portal_layout_values()
        receipt_ids = request.env['stock.picking'].search([
            ('picking_type_id.warehouse_id.partner_id', '=', request.env.user.partner_id.id),
            ('state', 'not in', ('draft', 'cancel', 'done')),
            ('picking_type_id.code', '=', 'incoming'),
            ('min_date', '>', (datetime.today() - relativedelta(months=6)).strftime(DEFAULT_SERVER_DATE_FORMAT)),
            ('min_date', '<', (datetime.today() + relativedelta(months=6)).strftime(DEFAULT_SERVER_DATE_FORMAT)),
        ])
        values.update({
            'receipts': receipt_ids,
        })
        return request.render('of_website_portal_carrier.of_website_portal_portal_my_receipts', values)

    @http.route(['/my/receipt/<int:receipt_id>'], type='http', auth='user', website=True)
    def portal_my_receipt(self, receipt_id=None, **kw):
        if receipt_id:
            values = super(WebsiteAccount, self)._prepare_portal_layout_values()
            receipt = request.env['stock.picking'].browse([receipt_id])
            if 'modal' in kw:
                action = receipt.sudo().do_new_transfer()
                wizard = request.env[action['res_model']].browse(action['res_id'])
                values.update({'wizard': wizard})
            values.update({'receipt': receipt})
            return request.render('of_website_portal_carrier.of_website_portal_portal_my_receipt', values)
        return request.redirect('/my/receipts')

    @http.route(['/my/receipt/<int:receipt_id>/validate'],
                type='http', auth='user', methods=['POST'], website=True, csrf=False)
    def portal_my_receipt_validate(self, receipt_id, **kw):
        kw.pop('csrf_token')
        values = kw
        receipt = request.env['stock.picking'].browse(receipt_id)

        for key in values:
            model, id = key.split('-')
            if model == 'stock.pack.operation':
                value = float(values[key])
                record = request.env[model].browse(int(id))
                record.qty_done = value
            elif model == 'stock.pack.operation.lot':
                value = values[key] == 'on'
                record = request.env[model].browse(int(id))
                record.qty = value and 1
                record.operation_id.qty_done += 1

        redirect = '/my/receipt/%s' % receipt_id
        attributes = []
        action = receipt.sudo().do_new_transfer()

        if action:
            attributes.append('modal=1')
        else:
            # On flag le BR comme validé par le transporteur
            receipt.of_validated_by_carrier = True
        if attributes:
            redirect = '%s?%s' % (redirect, '&'.join(attributes))

        return request.redirect(redirect)

    @http.route(['/my/receipt/<int:receipt_id>/create_backorder/<int:wizard_id>'],
                type='http', auth='user', methods=['POST'], website=True, csrf=False)
    def portal_my_receipt_create_backorder(self, receipt_id, wizard_id, **kw):
        kw.pop('csrf_token')
        wizard = request.env['stock.backorder.confirmation'].sudo().browse(wizard_id)
        operation_lot_obj = request.env['stock.pack.operation.lot'].sudo()
        mail_message_obj = request.env['mail.message'].sudo()
        attributes = []
        lots_data = []

        # On récupère le dernier message du RSE avant les modifications à venir
        last_message = mail_message_obj.search(
            [('model', '=', 'stock.picking'), ('res_id', '=', wizard.pick_id.id)], order='id desc', limit=1)

        # On récupère les lots non traités
        lots = wizard.pick_id.mapped('pack_operation_product_ids').filtered(
            lambda p: p.qty_done != p.product_qty).mapped('pack_lot_ids').filtered(lambda l: l.qty == 0)

        # On les sauvegarde pour les recréer plus tard dans le reliquat
        for lot in lots:
            lots_data.append({
                'qty': lot.qty,
                'qty_todo': lot.qty_todo,
                'lot_id': lot.lot_id,
            })

        try:
            wizard.process()
        except Exception:
            attributes.append('error=1')

        # On récupère le reliquat
        backorder = request.env['stock.picking'].search([('backorder_id', '=', wizard.pick_id.id)])

        # On recrée les stock.pack.operation.lot sur le reliquat
        for operation in backorder.pack_operation_product_ids:
            for data in lots_data:
                if data['lot_id'].product_id.id == operation.product_id.id:
                    operation_lot_obj.create({
                        'operation_id': operation.id,
                        'qty': data['qty'],
                        'qty_todo': data['qty_todo'],
                        'lot_id': data['lot_id'].id,
                    })

        # On flag le BR comme validé par le transporteur
        wizard.pick_id.of_validated_by_carrier = True

        # On met à jour le RSE avec les infos de l'utilisateur
        messages = mail_message_obj.search(
            [('model', '=', 'stock.picking'), ('res_id', 'in', [wizard.pick_id.id, backorder.id]),
             ('id', '>', last_message.id)])
        messages.write({'author_id': request.env.user.partner_id.id})

        redirect = '/my/receipt/%s' % receipt_id
        if attributes:
            redirect = '%s?%s' % (redirect, '&'.join(attributes))
        return request.redirect(redirect)

    @http.route(['/my/receipt/<int:receipt_id>/no_backorder/<int:wizard_id>'],
                type='http', auth='user', methods=['POST'], website=True, csrf=False)
    def portal_my_receipt_no_backorder(self, receipt_id, wizard_id, **kw):
        kw.pop('csrf_token')
        wizard = request.env['stock.backorder.confirmation'].sudo().browse(wizard_id)
        mail_message_obj = request.env['mail.message'].sudo()
        attributes = []

        # On récupère le dernier message du RSE avant les modifications à venir
        last_message = mail_message_obj.search(
            [('model', '=', 'stock.picking'), ('res_id', '=', wizard.pick_id.id)], order='id desc', limit=1)

        try:
            wizard.process_cancel_backorder()
        except Exception:
            attributes.append('error=1')

        # On flag le BR comme validé par le transporteur
        wizard.pick_id.of_validated_by_carrier = True

        # On met à jour le RSE avec les infos de l'utilisateur
        messages = mail_message_obj.search(
            [('model', '=', 'stock.picking'), ('res_id', '=', wizard.pick_id.id),
             ('id', '>', last_message.id)])
        messages.write({'author_id': request.env.user.partner_id.id})

        redirect = '/my/receipt/%s' % receipt_id
        if attributes:
            redirect = '%s?%s' % (redirect, '&'.join(attributes))
        return request.redirect(redirect)

    @http.route(['/my/receipt/pdf/<int:receipt_id>'], type='http', auth="user", website=True)
    def portal_get_receipt_pdf(self, receipt_id=None, **kw):
        receipt = request.env['stock.picking'].browse([receipt_id])
        try:
            receipt.check_access_rights('read')
            receipt.check_access_rule('read')
        except AccessError:
            return request.render('website.403')

        pack_ids = [int(key) for key in kw.keys()]
        packs = receipt.pack_operation_product_ids.filtered(lambda p: p.id in pack_ids)
        pdf = request.env['report'].get_pdf(packs.ids, 'of_website_portal_carrier.report_receipt_label')
        pdfhttpheaders = [
            ('Content-Type', 'application/pdf'), ('Content-Length', len(pdf)),
            ('Content-Disposition', 'attachment; filename=Etiquette.pdf;')
        ]
        return request.make_response(pdf, headers=pdfhttpheaders)

    @http.route(['/my/receipt/pdf/line/<int:pack_id>'], type='http', auth="user", website=True)
    def portal_get_receipt_line_pdf(self, pack_id=None, **kw):
        pack = request.env['stock.pack.operation'].browse([pack_id])
        try:
            pack.check_access_rights('read')
            pack.check_access_rule('read')
        except AccessError:
            return request.render('website.403')

        pdf = request.env['report'].get_pdf([pack_id], 'of_website_portal_carrier.report_receipt_label')
        pdfhttpheaders = [
            ('Content-Type', 'application/pdf'), ('Content-Length', len(pdf)),
            ('Content-Disposition', 'attachment; filename=Etiquette.pdf;')
        ]
        return request.make_response(pdf, headers=pdfhttpheaders)
