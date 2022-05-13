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
            fd, order_pdf = tempfile.mkstemp()
            os.write(fd, result)
            os.close(fd)
            file_paths = [order_pdf]

            mails_data = model._detect_doc_joint()

            for mail_data in mails_data:
                fd, mail_pdf = tempfile.mkstemp()
                os.write(fd, base64.b64decode(mail_data))
                os.close(fd)
                file_paths.append(mail_pdf)

            if report_name == 'sale.report_saleorder' and \
                    self.user_has_groups('of_sale.group_of_sale_print_attachment'):
                for attachment in model.order_line.mapped('of_product_attachment_ids'):
                    fd, attachment_pdf = tempfile.mkstemp()
                    os.write(fd, base64.b64decode(attachment.datas))
                    os.close(fd)
                    file_paths.append(attachment_pdf)

            if file_paths:
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
