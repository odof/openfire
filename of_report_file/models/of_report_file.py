# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.tools.safe_eval import safe_eval

import os
import base64
import tempfile

try:
    import pypdftk
except ImportError:
    pypdftk = None


class OFReportFile(models.Model):
    _name = 'of.report.file'
    _description = u"Dossier d'impression"

    name = fields.Char(string=u"Nom", required=True)
    active = fields.Boolean(string=u"Actif", default=True)
    model_id = fields.Many2one(comodel_name='ir.model', string=u"Modèle", required=True)
    corresponding_report_id = fields.Many2one(comodel_name='ir.actions.report.xml', string=u"Rapport associé")
    report_file_line_ids = fields.One2many(
        comodel_name='of.report.file.line', inverse_name='report_file_id', string=u"Éléments du dossier")

    @api.onchange('model_id')
    def _onchange_model_id(self):
        self.report_file_line_ids.unlink()

    @api.multi
    def toggle_active(self):
        super(OFReportFile, self).toggle_active()
        for record in self:
            if not record.active:
                # On désactive le rapport
                record.corresponding_report_id.unlink_action()
            else:
                # On réactive le rapport
                record.corresponding_report_id.create_action()

    @api.model
    def create(self, vals):
        record = super(OFReportFile, self).create(vals)
        # Création du rapport correspondant
        report = self.env['ir.actions.report.xml'].create({
            'name': record.name,
            'report_name': 'of_report_file.report_file_%04d' % record.id,
            'report_type': 'qweb-pdf',
            'model': record.model_id.model,
            })
        report.create_action()
        record.corresponding_report_id = report
        return record

    @api.multi
    def write(self, vals):
        res = super(OFReportFile, self).write(vals)
        if 'name' in vals or 'model_id' in vals:
            # Mise à jour du rapport correspondant
            for record in self:
                record.corresponding_report_id.write({
                    'name': record.name,
                    'model': record.model_id.model,
                })
                record.corresponding_report_id.unlink_action()
                record.corresponding_report_id.create_action()
        return res

    @api.multi
    def unlink(self):
        for report_file in self:
            report_file.corresponding_report_id.unlink()
        return super(OFReportFile, self).unlink()


class OFReportFileLine(models.Model):
    _name = 'of.report.file.line'
    _description = u"Élément de dossier d'impression"
    _order = 'sequence'

    report_file_id = fields.Many2one(
        comodel_name='of.report.file', string=u"Dossier", required=True, ondelete='cascade')
    sequence = fields.Integer(string=u"Séquence")
    type = fields.Selection(
        selection=[('qweb', u"Rapport PDF"), ('doc', u"Document joint")], string=u"Type", required=True)
    model = fields.Char(string=u"Nom du modèle")
    report_id = fields.Many2one(comodel_name='ir.actions.report.xml', string=u"Rapport PDF")
    combined_document_id = fields.Many2one(comodel_name='of.mail.template', string=u"Document joint")
    expr = fields.Char(
        string=u"Expression de sous-objet",
        help=u"Expression python permettant de retrouver le sous-objet concerné par cet élément, "
             u"utiliser le mot clé 'record' pour représenter l'objet depuis lequel le dossier est imprimé")
    expr_model = fields.Char(string=u"Nom du modèle du sous-objet")
    copy_nb = fields.Integer(string=u"Nombre d'exemplaires", default=1)

    @api.onchange('type', 'expr_model')
    def _onchange_type(self):
        self.report_id = False
        self.combined_document_id = False
        if self.type == 'qweb':
            if self.expr_model:
                self.model = self.expr_model
            else:
                self.model = self.report_file_id.model_id.model

    @api.multi
    def get_combined_doc(self, doc, obj):
        self.ensure_one()
        data = []
        if doc.file:
            # Utilisation des documents pdf fournis
            if not doc.chp_ids:
                data.append(doc.file)
            else:
                # Calcul des champs remplis sur le modèle de courrier
                attachment = self.env['ir.attachment'].search(
                    [('res_model', '=', doc._name),
                     ('res_field', '=', 'file'),
                     ('res_id', '=', doc.id)])
                datas = dict(self.env['of.compose.mail'].eval_champs(obj, doc.chp_ids))
                file_path = self.env['ir.attachment']._full_path(attachment.store_fname)
                fd, generated_pdf = tempfile.mkstemp(prefix='doc_joint_', suffix='.pdf')
                try:
                    pypdftk.fill_form(file_path, datas, out_file=generated_pdf, flatten=not doc.fillable)
                    with open(generated_pdf, "rb") as encode:
                        encoded_file = base64.b64encode(encode.read())
                finally:
                    os.close(fd)
                    try:
                        os.remove(generated_pdf)
                    except Exception:
                        pass
                data.append(encoded_file)
        return data and base64.b64decode(data[0]) or False


class Report(models.Model):
    _inherit = 'report'

    @api.model
    def get_pdf(self, docids, report_name, html=None, data=None):
        if report_name.split('.')[0] == 'of_report_file':
            report_file_id = int(report_name.split('_')[-1])
            report_file = self.env['of.report.file'].browse(report_file_id)

            tmp_results = []

            for line in report_file.report_file_line_ids:
                tmp_result = False
                obj_ids = docids
                model_name = report_file.model_id.model
                if line.expr:
                    objs = self.env[report_file.model_id.model].browse(docids)
                    res = safe_eval(line.expr, {'record': objs, 'self': self})
                    obj_ids = res.ids
                    model_name = line.expr_model

                if line.type == 'qweb':
                    tmp_result = super(Report, self).get_pdf(obj_ids, line.report_id.report_name, html=html, data=data)
                elif line.type == 'doc':
                    obj = self.env[model_name].browse(obj_ids)
                    tmp_result = line.get_combined_doc(line.combined_document_id, obj)

                if tmp_result:
                    for i in range(line.copy_nb):
                        tmp_results.append(tmp_result)

            result = tmp_results and tmp_results[0] or False
            file_paths = []

            for data in tmp_results:
                fd, tmp_pdf = tempfile.mkstemp()
                os.write(fd, data)
                os.close(fd)
                file_paths.append(tmp_pdf)

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
        else:
            result = super(Report, self).get_pdf(docids, report_name, html=html, data=data)
        return result
