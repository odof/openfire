# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class OFPickingMassValidationWizard(models.TransientModel):
    _name = 'of.picking.mass.validation.wizard'
    _description = u"Validation en masse des stock pickings"

    show_date = fields.Boolean(
        default=lambda t: bool(t.env['ir.values'].get_default('stock.config.settings', 'of_forcer_date_move')))
    date_done = fields.Date(string=u"Date du transfert", default=fields.Date.today, required=True)

    @api.multi
    def button_validate(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', []) or []
        nb_active = len(active_ids)
        picking_obj = self.env['stock.picking']
        transfer_obj = self.env['stock.immediate.transfer']

        unwanted_pickings = picking_obj
        keep_pickings = picking_obj.browse(active_ids).\
            filtered(lambda r: r.state in ('waiting', 'partially_available', 'assigned', 'confirmed'))

        if self.user_has_groups('stock.group_production_lot'):
            unwanted_pickings = keep_pickings.mapped('pack_operation_product_ids').filtered(
                lambda l: l.product_id and l.product_id.tracking == 'lot').mapped('picking_id')
            keep_pickings = keep_pickings - unwanted_pickings

        nb_unwanted = len(unwanted_pickings)
        today = fields.Date.today()
        if self.date_done > today:
            raise UserError(u"Vous ne pouvez pas valider votre transfert à une date future.")

        done_picking_ids = []
        error_picking_ids = []

        for record in keep_pickings:
            try:
                record.pack_operation_product_ids.write({'qty_done': 0.0})
                record.force_assign()
                new_transfer = transfer_obj.create({'pick_id': record.id, 'date_done': self.date_done})
                if new_transfer.date_done != today:
                    new_transfer = new_transfer.with_context({'force_date_done': self.date_done})
                new_transfer.process()
            except Exception as e:
                _logger.info(u"Erreur lors de la validation du BL / BR %s" % record.name)
                error_msg = e.name if hasattr(e, 'name') else e.message
                _logger.exception(error_msg)
                error_picking_ids.append((record.name, error_msg))
                self._cr.rollback()
            else:
                done_picking_ids.append(record.id)
                self._cr.commit()  # On commit pour éviter de bloquer les autres BL / BR en cas d'erreur

        msg_success_str = u" ont été validés" if len(done_picking_ids) > 1 else u" a été validé"
        msg_not_processed_str = ''
        msg_error_str = ''
        if nb_unwanted:
            msg_not_processed_str = u"Les BL / BR sélectionnés n'ayant pas été validés n'étaient" \
                u" soit pas dans le bon statut, ou incluaient un article géré au lot"
        if error_picking_ids:
            msg_error_str = u"Des erreurs sont survenues lors de la validation des BL / BR suivants : \n%s" % \
                u"\n".join([u"- %s : %s" % (picking_name, error) for picking_name, error in error_picking_ids])
        message = \
            u"Sur les %s BL / BR sélectionnés : \n%s%s\n\n%s\n\n%s" % (
                nb_active, len(done_picking_ids), msg_success_str, msg_not_processed_str, msg_error_str)
        return self.env['of.popup.wizard'].popup_return(message)
