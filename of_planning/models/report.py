# -*- coding: utf-8 -*-

import logging
import os
import base64
import tempfile
from datetime import datetime

from odoo import api, models, fields, _
from odoo.tools.safe_eval import safe_eval

try:
    import pypdftk
except ImportError:
    pypdftk = None

_logger = logging.getLogger(__name__)

class Report(models.Model):
    _inherit = "report"

    @api.model
    def get_pdf(self, docids, report_name, html=None, data=None):
        result = super(Report, self).get_pdf(docids, report_name, html=html, data=data)
        if report_name in self.env['of.planning.intervention']._allowed_reports_template():
            # On ajoute au besoin les documents joint
            rdv = self.env['of.planning.intervention'].browse(docids)[0]
            mails_data = rdv._detect_doc_joint_template(report_name)
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

#of_planning.of_planning_raport_intervention_report

    @api.model
    def _check_attachment_use(self, docids, report):
        def attachment_filenames(records, report):
            # adapted from _attachment_filenames in odoo-ocb/addons/report/models/report.py
            return dict((record.id, safe_eval(report.print_report_name, {'object': record})) for record in records)

        def attachment_stored(records, report, filenames):
            # adapted from _attachment_stored in odoo-ocb/addons/report/models/report.py
            return dict((record.id, self.env['ir.attachment'].search([
                ('datas_fname', '=', filenames[record.id]),
                ('res_model', '=', report.model),
                ('res_id', '=', record.id)
                ], limit=1)) for record in records)

        if report.report_name == 'of_planning.of_planning_rapport_intervention_report_template':
            default_template = self.env.ref(
                'of_planning.of_planning_default_intervention_template', raise_if_not_found=False)
            save_in_attachment = {}
            save_in_attachment['model'] = report.model
            save_in_attachment['loaded_documents'] = {}
            # we only apply this rule for interventions in state == 'done'
            records = self.env[report.model].browse(docids)
            if not self._context.get('force_attachment', False):
                records = records.filtered(lambda r: r.state == 'done')
            filenames = attachment_filenames(records, report)
            attachments = attachment_stored(records, report, filenames)
            record_template = dict((record.id, record.template_id or default_template) for record in records)
            for record_id, template in record_template.iteritems():
                filename = filenames[record_id]

                # If the user has checked 'Reload from Attachment'
                if attachments:
                    attachment = attachments[record_id]
                    if attachment:
                        # Add the loaded pdf in the loaded_documents list
                        pdf = attachment.datas
                        pdf = base64.decodestring(pdf)
                        save_in_attachment['loaded_documents'][record_id] = pdf
                        _logger.info('The PDF document %s was loaded from the database' % filename)

                        continue  # Do not save this document as we already ignore it

                # If the user has checked 'Save as Attachment Prefix'
                if (self._context.get('force_attachment', False) or template.attach_report) and not filename is False:
                    save_in_attachment[record_id] = filename  # Mark current document to be saved
            others = super(Report, self)._check_attachment_use(list(set(docids) - set(records._ids)), report)
            save_in_attachment.update(others)
            return save_in_attachment
        else:
            return super(Report, self)._check_attachment_use(docids, report)

