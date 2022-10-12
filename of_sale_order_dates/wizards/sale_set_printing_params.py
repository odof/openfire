# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models, fields, api


class OFSaleWizardSetPrintingParams(models.TransientModel):
    _inherit = 'of.sale.wizard.set.printing.params'

    @api.model
    def _auto_init(self):
        """ Version 10.0.2.0.0 : new version of PDf printing settings (fields and data migration).
        """
        IrValues = self.env['ir.values']
        current_module = self.env['ir.module.module'].search([('name', '=', 'of_sale_order_dates')])
        latest_version = current_module.latest_version
        if latest_version < '10.0.2.0.0':
            mapping_data_dict = {
                'pdf_requested_week': {'default_value': False, 'oldname': 'of_pdf_display_requested_week'},
            }
            to_unlink = [data['oldname'] for data in mapping_data_dict.values() if data['oldname']]
            current_values = {}
            for current_name in to_unlink:
                current_values[current_name] = IrValues.get_default('sale.config.settings', current_name)

        res = super(OFSaleWizardSetPrintingParams, self)._auto_init()

        if latest_version < '10.0.2.0.0':
            # create new settings or update existing ones
            for name, data in mapping_data_dict.items():
                if data['oldname'] and data['oldname'] in current_values and \
                        IrValues.get_default('sale.config.settings', data['oldname']) is not None:
                    value = current_values.get(data['oldname'])
                    IrValues.set_default('sale.config.settings', name, value)
                elif not data['oldname'] and IrValues.get_default('sale.config.settings', name) is None:
                    IrValues.set_default('sale.config.settings', name, data['default_value'])
                else:
                    IrValues.set_default('sale.config.settings', name, data['default_value'])
            # delete old settings
            IrValues.search([('model', '=', 'sale.config.settings'), ('name', 'in', to_unlink)]).unlink()
        return res

    pdf_requested_week = fields.Boolean(
        string="Requested week", default=False, help="If checked, displays the requested week under the payment terms.")

    @api.multi
    def set_pdf_requested_week(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'pdf_requested_week', self.pdf_requested_week)
