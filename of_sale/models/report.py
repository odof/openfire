# -*- coding: utf-8 -*-
import os
import base64
import tempfile
from odoo import models, api


class Report(models.Model):
    _inherit = "report"

    @api.model
    def get_pdf(self, docids, report_name, html=None, data=None):
        result = super(Report, self).get_pdf(docids, report_name, html=html, data=data)
        allowed_reports = self.env['of.documents.joints']._allowed_reports()
        if report_name in allowed_reports:
            # On ajoute au besoin les documents joint
            model = self.env[allowed_reports[report_name]].browse(docids)[0]
            report_id = self._get_report_from_name(report_name)
            if report_id.of_mail_template_ids:
                # le rapport possède des documents joints, ils prennent le pas sur ceux de l'enregistrement
                mails_data = model.with_context(force_of_mail_template_ids=report_id.of_mail_template_ids._ids). \
                    _detect_doc_joint()
            else:
                mails_data = model._detect_doc_joint()

            # Médiathèques produit, prise en compte des PJ
            product_attachments = False
            if report_name == 'sale.report_saleorder' and self.user_has_groups(
                    'of_sale.group_of_sale_print_attachment'):
                product_attachments = model.order_line.mapped('of_product_attachment_ids')

            if mails_data or product_attachments:
                fd, order_pdf = tempfile.mkstemp()
                os.write(fd, result)
                os.close(fd)
                file_paths = [order_pdf]

                if mails_data:
                    for mail_data in mails_data:
                        fd, mail_pdf = tempfile.mkstemp()
                        os.write(fd, base64.b64decode(mail_data))
                        os.close(fd)
                        file_paths.append(mail_pdf)

                if product_attachments:
                    for attachment in product_attachments:
                        fd, attachment_pdf = tempfile.mkstemp()
                        os.write(fd, base64.b64decode(attachment.datas))
                        os.close(fd)
                        file_paths.append(attachment_pdf)

                result_file_path = self.env['report']._merge_pdf(file_paths)
                try:
                    result_file = file(result_file_path, "rb")
                    result = result_file.read()
                    result_file.close()
                    for file_path in file_paths:
                        os.remove(file_path)
                    os.remove(result_file_path)
                except Exception:
                    pass

        return result


class IrActionsReportXml(models.Model):
    _name = 'ir.actions.report.xml'
    _inherit = ['ir.actions.report.xml', 'of.documents.joints']
