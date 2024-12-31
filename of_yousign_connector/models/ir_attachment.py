# -*- coding: utf-8 -*-

from odoo import api, fields, models


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    of_yousign_report = fields.Boolean(string="Yousign report")
    # of_one_signatory_only = fields.Boolean(string="One signatory only (Yousign)")
    of_yousign_order = fields.Integer(string="Yousign order", default=999)
    of_ys_identifier = fields.Char(string="Yousign ID")

    @api.model
    def _get_yousign_reports(self):
        return ["of_yousign_connector.sale_order_electronic_signature_report"]

    @api.model_create_multi
    def create(self, vals_list):
        yousign_reports = self._get_yousign_reports()
        is_yousign_report = self._context.get("report_name") in yousign_reports
        if is_yousign_report:
            for vals in vals_list:
                vals["of_yousign_report"] = True
        return super(IrAttachment, self).create(vals_list)
