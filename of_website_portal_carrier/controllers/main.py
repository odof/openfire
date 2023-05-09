# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import http
from odoo import fields
from odoo.http import request
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.exceptions import UserError
from odoo.addons.website_portal.controllers.main import website_account


class WebsiteAccount(website_account):

    def _prepare_portal_layout_values(self):
        values = super(WebsiteAccount, self)._prepare_portal_layout_values()
        if request.env.user.has_group('of_website_portal_carrier.group_of_carrier_portal'):
            receipt_ids = request.env['stock.picking'].search([
                ('picking_type_id.warehouse_id.partner_id', '=', request.env.user.partner_id.id),
                ('state', 'not in', ('draft', 'cancel', 'done')),
                ('picking_type_id.code', '=', 'incoming'),
                ('min_date', '>', (datetime.today() - relativedelta(months=2)).strftime(DEFAULT_SERVER_DATE_FORMAT)),
                ('min_date', '<', (datetime.today() + relativedelta(months=2)).strftime(DEFAULT_SERVER_DATE_FORMAT)),
            ])
            values.update({
                'receipt_count': len(receipt_ids),
            })
        return values

    @http.route(['/my/receipts'], type='http', auth='user', website=True)
    def portal_my_receipts(self):
        if request.env.user.has_group('of_website_portal_carrier.group_of_carrier_portal'):
            values = self._prepare_portal_layout_values()
            receipt_ids = request.env['stock.picking'].search([
                ('picking_type_id.warehouse_id.partner_id', '=', request.env.user.partner_id.id),
                ('state', 'not in', ('draft', 'cancel', 'done')),
                ('picking_type_id.code', '=', 'incoming'),
                ('min_date', '>', (datetime.today() - relativedelta(months=2)).strftime(DEFAULT_SERVER_DATE_FORMAT)),
                ('min_date', '<', (datetime.today() + relativedelta(months=2)).strftime(DEFAULT_SERVER_DATE_FORMAT)),
            ])
            values.update({
                'receipts': receipt_ids,
            })
            return request.render('of_website_portal_carrier.of_website_portal_portal_my_receipts', values)
        else:
            return request.redirect('/my/home')

    @http.route(['/my/receipt/<int:receipt_id>'], type='http', auth='user', website=True)
    def portal_my_receipt(self, receipt_id=None, **kw):
        if request.env.user.has_group('of_website_portal_carrier.group_of_carrier_portal'):
            if receipt_id:
                values = super(WebsiteAccount, self)._prepare_portal_layout_values()
                receipt = request.env['stock.picking'].search([('id', '=', receipt_id)])
                if receipt:
                    receipt = receipt.sudo()
                    if 'modal' in kw:
                        action = False
                        try:
                            action = receipt.do_new_transfer()
                        except UserError as e:
                            receipt.write({'of_error_message': u"Attention, pour réceptionner des articles identifiés "
                                                               u"par N° de série, veuillez cocher la case Qté reçue."})
                        if action:  # validation works
                            wizard = request.env[action['res_model']].browse(action['res_id'])
                            values.update({'wizard': wizard})
                        else:  # error while validating, need to redirect
                            values.update({'receipt': receipt})
                            return request.redirect('/my/receipt/%i' % receipt_id)
                values.update({'receipt': receipt})
                return request.render('of_website_portal_carrier.of_website_portal_portal_my_receipt', values)
            return request.redirect('/my/receipts')
        else:
            return request.redirect('/my/home')

    @http.route(['/my/receipt/<int:receipt_id>/validate'],
                type='http', auth='user', methods=['POST'], website=True, csrf=False)
    def portal_my_receipt_validate(self, receipt_id, **kw):
        kw.pop('csrf_token')
        rollback = 'rollback' in kw and kw.pop('rollback')
        values = kw
        receipt = request.env['stock.picking'].search([('id', '=', receipt_id)]).sudo()
        if rollback:
            receipt.of_carrier_validation_date = False
            redirect = '/my/receipt/%s' % receipt_id
            return request.redirect(redirect)

        pack_op_to_update = request.env['stock.pack.operation'].sudo()
        for key in values:
            model, id = key.split('-')
            if model == 'stock.pack.operation':
                value = float(values[key])
                record = request.env[model].sudo().search([('id', '=', int(id))])
                if record:
                    record.qty_done = value
            elif model == 'stock.pack.operation.lot':
                value = values[key] == 'on'
                record = request.env[model].sudo().search([('id', '=', int(id))])
                if record:
                    record.qty = value and 1
                    pack_op_to_update |= record.operation_id

        # à faire après pour ne le faire qu'une fois par stock.pack.operation
        for pack_op in pack_op_to_update:
            pack_op.qty_done = sum(pack_op.pack_lot_ids.mapped('qty'))

        redirect = '/my/receipt/%s' % receipt_id
        attributes = []
        delay = request.env['ir.values'].sudo().get_default('website.config.settings', 'of_picking_rollback_delay')
        action = False
        if not delay:
            try:
                action = receipt.do_new_transfer()
            except UserError as e:
                receipt.write({'of_error_message': u"Attention, pour réceptionner des articles identifiés par N°"
                                                          u" de série, veuillez cocher la case Qté reçue."})
        else:
            action = receipt.check_backorder()
            if not action:
                receipt.of_carrier_validation_date = fields.Datetime.now()

        if action:
            attributes.append('modal=1')
        elif not delay:
            # On flag le BR comme validé par le transporteur
            receipt.of_validated_by_carrier = True
        if attributes:
            redirect = '%s?%s' % (redirect, '&'.join(attributes))

        return request.redirect(redirect)

    @http.route(['/my/receipt/<int:receipt_id>/create_backorder/<int:wizard_id>'],
                type='http', auth='user', methods=['POST'], website=True, csrf=False)
    def portal_my_receipt_create_backorder(self, receipt_id, wizard_id, **kw):
        kw.pop('csrf_token')
        delay = request.env['ir.values'].sudo().get_default('website.config.settings', 'of_picking_rollback_delay')
        if delay:
            # Un délai existe, il faut taguer le BL pour que le backorder soit créé puis renvoyer le picking
            receipt = request.env['stock.picking'].browse(receipt_id)
            receipt.of_need_backorder = True
            receipt.of_carrier_validation_date = fields.Datetime.now()
            redirect = '/my/receipt/%s' % receipt_id
            return request.redirect(redirect)
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
        delay = request.env['ir.values'].sudo().get_default('website.config.settings', 'of_picking_rollback_delay')
        if delay:
            # Un délai existe, juste renvoyer le picking
            receipt = request.env['stock.picking'].browse(receipt_id)
            receipt.of_need_backorder = False
            receipt.of_carrier_validation_date = fields.Datetime.now()
            redirect = '/my/receipt/%s' % receipt_id
            return request.redirect(redirect)
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
        receipt = request.env['stock.picking'].search([('id', '=', receipt_id)])
        if not receipt:
            return request.render('website.403')

        pack_ids = [int(key) for key in kw.keys()]
        packs = receipt.sudo().pack_operation_product_ids.filtered(lambda p: p.id in pack_ids)
        pdf = request.env['report'].sudo().get_pdf(packs.ids, 'of_website_portal_carrier.report_receipt_label')
        pdfhttpheaders = [
            ('Content-Type', 'application/pdf'), ('Content-Length', len(pdf)),
            ('Content-Disposition', 'attachment; filename=Etiquette.pdf;')
        ]
        return request.make_response(pdf, headers=pdfhttpheaders)

    @http.route(['/my/receipt/pdf/line/<int:pack_id>'], type='http', auth="user", website=True)
    def portal_get_receipt_line_pdf(self, pack_id=None, **kw):
        pack = request.env['stock.pack.operation'].search([('id', '=', pack_id)])
        if not pack:
            return request.render('website.403')

        pdf = request.env['report'].sudo().get_pdf([pack_id], 'of_website_portal_carrier.report_receipt_label')
        pdfhttpheaders = [
            ('Content-Type', 'application/pdf'), ('Content-Length', len(pdf)),
            ('Content-Disposition', 'attachment; filename=Etiquette.pdf;')
        ]
        return request.make_response(pdf, headers=pdfhttpheaders)
