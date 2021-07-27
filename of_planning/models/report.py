# -*- coding: utf-8 -*-

from odoo import api, models, fields, _
import os
import base64
import tempfile
try:
    import pypdftk
except ImportError:
    pypdftk = None


class Report(models.Model):
    _inherit = "report"

    @api.model
    def get_pdf(self, docids, report_name, html=None, data=None):
        result = super(Report, self).get_pdf(docids, report_name, html=html, data=data)
        if report_name in self.env['of.planning.intervention']._allowed_reports():
            # On ajoute au besoin les documents joint
            rdv = self.env['of.planning.intervention'].browse(docids)[0]
            mails_data = rdv._detect_doc_joint(report_name)
            if mails_data:
                fd, order_pdf = tempfile.mkstemp()
                os.write(fd, result)
                os.close(fd)
                file_paths = [order_pdf]

                for mail_data in mails_data:
                    fd, mail_pdf = tempfile.mkstemp()
                    os.write(fd, base64.b64decode(mail_data))
                    os.close(fd)
                    file_paths.append(mail_pdf)

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
