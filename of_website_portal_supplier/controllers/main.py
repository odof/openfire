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
        if request.env.user.has_group('of_website_portal_supplier.group_of_supplier_portal'):
            shipment_ids = request.env['stock.picking'].search([
                ('partner_id', '=', request.env.user.partner_id.id),
                ('state', '=', 'assigned'),
                ('picking_type_id.code', '=', 'incoming'),
                ('min_date', '>', (datetime.today() - relativedelta(months=2)).strftime(DEFAULT_SERVER_DATE_FORMAT)),
                ('min_date', '<', (datetime.today() + relativedelta(months=2)).strftime(DEFAULT_SERVER_DATE_FORMAT)),
            ])
            values.update({
                'shipment_count': len(shipment_ids),
            })
        return values

    @http.route(['/my/shipments'], type='http', auth='user', website=True)
    def portal_my_shipments(self):
        if request.env.user.has_group('of_website_portal_supplier.group_of_supplier_portal'):
            values = self._prepare_portal_layout_values()
            shipment_ids = request.env['stock.picking'].search([
                ('partner_id', '=', request.env.user.partner_id.id),
                ('state', '=', 'assigned'),
                ('picking_type_id.code', '=', 'incoming'),
                ('min_date', '>', (datetime.today() - relativedelta(months=2)).strftime(DEFAULT_SERVER_DATE_FORMAT)),
                ('min_date', '<', (datetime.today() + relativedelta(months=2)).strftime(DEFAULT_SERVER_DATE_FORMAT)),
            ])
            values.update({
                'shipments': shipment_ids,
            })
            return request.render('of_website_portal_supplier.of_website_portal_portal_my_shipments', values)
        else:
            return request.redirect('/my/home')

    @http.route(['/my/shipment/<int:shipment_id>'], type='http', auth='user', website=True)
    def portal_my_shipment(self, shipment_id=None, **kw):
        if request.env.user.has_group('of_website_portal_supplier.group_of_supplier_portal'):
            values = super(WebsiteAccount, self)._prepare_portal_layout_values()
            shipment = request.env['stock.picking'].search([('id', '=', shipment_id)])
            if shipment:
                shipment = shipment.sudo()
                if 'modal' in kw:
                    action = False
                    try:
                        action = shipment.action_delivery_division()
                    except UserError:
                        pass
                    if action:  # validation works
                        wizard = request.env[action['res_model']].browse(action['res_id'])
                        values.update({'wizard': wizard})
                    else:  # error while validating, need to redirect
                        values.update({'shipment': shipment})
                        return request.redirect('/my/receipt/%i' % shipment)
                values.update({'shipment': shipment})
                return request.render('of_website_portal_supplier.of_website_portal_portal_my_shipment', values)
            else:
                return request.redirect('/my/shipments')
        else:
            return request.redirect('/my/home')

    @http.route(['/my/shipment/<int:shipment_id>/save'],
                type='http', auth='user', methods=['POST'], website=True, csrf=False)
    def portal_my_shipment_save(self, shipment_id, **kw):
        """
        Si c'est uniquement une sauvegarde, on ne procède pas à l'expédition
        """
        kw['no_ship'] = True
        self.portal_my_shipment_validate(shipment_id, **kw)

    @http.route(['/my/shipment/<int:shipment_id>/validate'],
                type='http', auth='user', methods=['POST'], website=True, csrf=False)
    def portal_my_shipment_validate(self, shipment_id, **kw):
        """
        Si c'est uniquement une sauvegarde, on ne procède pas à l'expédition
        """
        kw.pop('csrf_token')
        rollback = 'rollback' in kw and kw.pop('rollback')
        no_ship = 'no_ship' in kw and kw.pop('no_ship')
        values = kw
        shipment = request.env['stock.picking'].search([('id', '=', shipment_id)]).sudo()
        if rollback:
            shipment.of_shipment_date = False
            redirect = '/my/shipment/%s' % shipment_id
            return request.redirect(redirect)

        pack_op_to_update = request.env['stock.pack.operation'].sudo()
        tracking_value_obj = request.env['mail.tracking.value'].sudo()

        # On crée le message RSE
        message = request.env['mail.message'].sudo().create({
            'author_id': request.env.user.partner_id.id,
            'model': 'stock.picking',
            'res_id': shipment.id,
            'type': 'notification',
            'subtype_id': request.env.ref('mail.mt_note').id,
            'body': u"Ce transfert %s a été modifié: " % shipment.name,
            'date': fields.Datetime.now(),
        })

        # On met à jour les valeur du BR avec date et quantité d'expédition
        for key in values:
            type, model, id = key.split('-')
            if model == 'stock.pack.operation':
                if type == 'date':
                    value = values[key]
                    if not value:
                        value = False
                    record = request.env[model].sudo().search([('id', '=', int(id))])
                    if record and record.of_expected_shipment_date != value:
                        tracking_value_obj.create({
                            'mail_message_id': message.id,
                            'field': 'of_expected_shipment_date',
                            'field_desc': u"[%s] Date d'expédition prévue" % record.product_id.default_code,
                            'field_type': 'date',
                            'old_value_datetime': record.of_expected_shipment_date,
                            'new_value_datetime': value,
                        })
                        record.of_expected_shipment_date = value
                else:
                    value = float(values[key])
                    record = request.env[model].sudo().search([('id', '=', int(id))])
                    if record and record.of_shipped_qty != value:
                        tracking_value_obj.create({
                            'mail_message_id': message.id,
                            'field': 'of_shipped_qty',
                            'field_desc': u"[%s] Qté d'expédiée" % record.product_id.default_code,
                            'field_type': 'integer',
                            'old_value_integer': record.of_shipped_qty,
                            'new_value_integer': value,
                        })
                        record.of_shipped_qty = value
            elif model == 'stock.pack.operation.lot':
                if type == 'date':
                    value = values[key]
                    if not value:
                        value = False
                    record = request.env[model].sudo().search([('id', '=', int(id))])
                    if record and record.of_expected_shipment_date != value:
                        tracking_value_obj.create({
                            'mail_message_id': message.id,
                            'field': 'of_expected_shipment_date',
                            'field_desc': u"[Lot %s] Date d'expédition prévue" % record.of_internal_serial_number,
                            'field_type': 'date',
                            'old_value_datetime': record.of_expected_shipment_date,
                            'new_value_datetime': value,
                        })
                        record.of_expected_shipment_date = value
                else:
                    value = values[key] == 'on'
                    record = request.env[model].sudo().search([('id', '=', int(id))])
                    if record and record.of_shipped_qty != value:
                        tracking_value_obj.create({
                            'mail_message_id': message.id,
                            'field': 'of_shipped_qty',
                            'field_desc': u"[Lot %s] Qté d'expédiée" % record.of_internal_serial_number,
                            'field_type': 'integer',
                            'old_value_integer': record.of_shipped_qty,
                            'new_value_integer': value and 1,
                        })
                        record.of_shipped_qty = value and 1
                        pack_op_to_update |= record.operation_id

        # à faire après pour ne le faire qu'une fois par stock.pack.operation
        for pack_op in pack_op_to_update:
            pack_op.of_shipped_qty = sum(pack_op.pack_lot_ids.mapped('of_shipped_qty'))

        redirect = '/my/shipment/%s' % shipment_id

        # Si l'attribut no_ship est présent, on ne procède pas à l'expédition
        if no_ship:
            return request.redirect(redirect)

        action = False
        attributes = []
        delay = request.env['ir.values'].sudo().get_default(
            'website.config.settings', 'of_picking_rollback_delay_minutes_supplier')
        need_division = any(
            [po_line.product_qty != po_line.of_shipped_qty for po_line in shipment.pack_operation_product_ids])

        # Si besoin de division, on passera par une popup de confirmation
        if need_division:
            try:
                action = shipment.action_delivery_division()
            except UserError:
                pass

        # Si le BR n'a pas besoin de division, on peut déjà renseigner la date d'expédition
        else:
            shipment.of_shipment_date = fields.Datetime.now()
            # Si aucun délai, on peut même flag le BR comme expédié par le fournisseur
            if not delay:
                shipment.of_shipped_by_supplier = True

        if action:
            attributes.append('modal=1')
        if attributes:
            redirect = '%s?%s' % (redirect, '&'.join(attributes))

        return request.redirect(redirect)

    @http.route(['/my/shipment/<int:shipment_id>/divide_picking/<int:wizard_id>'],
                type='http', auth='user', methods=['POST'], website=True, csrf=False)
    def portal_my_shipment_divide_picking(self, shipment_id, wizard_id, **kw):
        kw.pop('csrf_token')
        delay = request.env['ir.values'].sudo().get_default(
            'website.config.settings', 'of_picking_rollback_delay_minutes_supplier')
        shipment = request.env['stock.picking'].browse(shipment_id)
        if delay:
            # Un délai existe, il faut taguer le BR pour que la division soit créé puis renvoyer le picking
            shipment.of_shipment_date = fields.Datetime.now()
            redirect = '/my/shipment/%s' % shipment_id
            return request.redirect(redirect)

        # Si pas de délai, on traite tout de suite
        picking_obj = request.env['stock.picking'].sudo()
        operation_lot_obj = request.env['stock.pack.operation.lot'].sudo()
        mail_message_obj = request.env['mail.message'].sudo()
        attributes = []

        # On récupère le dernier message du RSE avant les modifications à venir
        last_message = mail_message_obj.search(
            [('model', '=', 'stock.picking'), ('res_id', '=', shipment.id)], order='id desc', limit=1)

        operations_data = shipment._prepare_division_values()
        move_to_unreserve = shipment.sudo().move_lines.filtered(
            lambda ml: all(qty != 0 for qty in ml.mapped(
                'linked_move_operation_ids.operation_id.of_shipped_qty')))

        try:
            # On annule les réservations
            move_to_unreserve.sudo().action_reset()
            wizard = request.env['of.delivery.division.wizard'].sudo().browse(wizard_id)
            for line in wizard.line_ids:
                for operation in operations_data['new_picking']:
                    if operation['product_id'] == line.product_id:
                        line.qty_to_divide = operation['product_qty']

            # On divise
            new_action = wizard.sudo().action_delivery_division()

            if new_action:
                # On recrée les opérations et lots
                shipment.sudo().action_assign()
                for line in shipment.pack_operation_product_ids:
                    for operation in operations_data['old_picking']:
                        if operation['product_id'] == line.product_id:
                            line.write({
                                'of_shipped_qty': operation['of_shipped_qty'],
                                'of_expected_shipment_date': operation['of_expected_shipment_date'],
                            })
                            for lot in operation['pack_lot_ids']:
                                lot_data = lot
                                lot_data['operation_id'] = line.id
                                operation_lot_obj.create(lot_data)

                new_picking = picking_obj.browse(new_action['res_id'])
                new_picking.sudo().action_assign()
                for line in new_picking.pack_operation_product_ids:
                    for operation in operations_data['new_picking']:
                        if operation['product_id'] == line.product_id:
                            line.write({
                                'of_shipped_qty': operation['of_shipped_qty'],
                                'of_expected_shipment_date': operation['of_expected_shipment_date'],
                            })
                            for lot in operation['pack_lot_ids']:
                                lot_data = lot
                                lot_data['operation_id'] = line.id
                                operation_lot_obj.create(lot_data)

            # On flag le BR comme expédié par le fournisseur
            shipment.write({
                'of_shipment_date': fields.Datetime.now(),
                'of_shipped_by_supplier': True,
            })

            # On met à jour le RSE avec les infos de l'utilisateur
            messages = mail_message_obj.search(
                [('model', '=', 'stock.picking'), ('res_id', 'in', [shipment.id, new_picking.id]),
                 ('id', '>', last_message.id)])
            messages.write({'author_id': request.env.user.partner_id.id})
        except Exception:
            attributes.append('error=1')

        redirect = '/my/shipment/%s' % shipment_id
        if attributes:
            redirect = '%s?%s' % (redirect, '&'.join(attributes))
        return request.redirect(redirect)

    @http.route(['/my/shipment/pdf/<int:shipment_id>'], type='http', auth="user", website=True)
    def portal_get_shipment_pdf(self, shipment_id=None, **kw):
        """ Impression des étiquettes à partir du BR """
        shipment = request.env['stock.picking'].search([('id', '=', shipment_id)])
        if not shipment:
            return request.render('website.403')

        pack_ids = [int(key) for key in kw.keys()]
        packs = shipment.sudo().pack_operation_product_ids.filtered(lambda p: p.id in pack_ids)
        pdf = request.env['report'].sudo().get_pdf(packs.ids, 'of_website_portal.report_label')
        pdfhttpheaders = [
            ('Content-Type', 'application/pdf'), ('Content-Length', len(pdf)),
            ('Content-Disposition', 'attachment; filename=Etiquette.pdf;')
        ]
        return request.make_response(pdf, headers=pdfhttpheaders)

    @http.route(['/my/shipment/pdf/line/<int:pack_id>'], type='http', auth="user", website=True)
    def portal_get_shipment_line_pdf(self, pack_id=None, **kw):
        """ Impression des étiquettes à partir des opérations du BR """
        pack = request.env['stock.pack.operation'].search([('id', '=', pack_id)])
        if not pack:
            return request.render('website.403')

        pdf = request.env['report'].sudo().get_pdf([pack_id], 'of_website_portal.report_label')
        pdfhttpheaders = [
            ('Content-Type', 'application/pdf'), ('Content-Length', len(pdf)),
            ('Content-Disposition', 'attachment; filename=Etiquette.pdf;')
        ]
        return request.make_response(pdf, headers=pdfhttpheaders)
