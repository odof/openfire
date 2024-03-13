# -*- coding: utf-8 -*-

from odoo.http import Controller, route, request
from odoo.addons.web.controllers.main import _serialize_exception, content_disposition
import tempfile
import os
import base64


class Main(Controller):

    def print_acrobat(self, template, model):
        """
        Impression de modèle de courrier avec fichier joint. Calcul de champs si PDF éditable
        :param template: Modèle de courrier utilisé
        :param model: objet sur lequel le calcul de champ est basé
        :return: PDF sous forme de chaine de caractères
        """
        template_file = False
        compose_mail_obj = request.env['of.compose.mail']
        attachment_obj = request.env['ir.attachment']
        if not template.chp_ids:
            template_file = base64.b64decode(template.file)
        else:
            attachment = attachment_obj.search([('res_model', '=', template._name),
                                                ('res_field', '=', 'file'),
                                                ('res_id', '=', template.id)])
            datas = dict(compose_mail_obj.eval_champs(model, template.chp_ids))
            file_path = attachment_obj._full_path(attachment.store_fname)
            fd, generated_pdf = tempfile.mkstemp(prefix='doc_joint_', suffix='.pdf')
            try:
                compose_mail_obj.fill_form(model, file_path, datas, generated_pdf, template)
                with open(generated_pdf, "rb") as encode:
                    template_file = encode.read()
            finally:
                os.close(fd)
                try:
                    os.remove(generated_pdf)
                except Exception:
                    pass

        return template_file

    def print_report(self, template, model):
        """
        Impression de modèle de courrier plein texte
        :param template: Modèle de courrier utilisé
        :param model: objet sur lequel le calcul de champ est basé
        :return: PDF sous forme de chaine de caractères
        """
        compose_mail_obj = request.env['of.compose.mail']
        report_obj = request.env['ir.actions.report.xml']
        content = compose_mail_obj.eval_text(model, template.body_text)
        data = {
            'ids': model._ids,
            'model': model._name,
            'form': {
                'lettre_id' : (template.id, template.name),
                'content' : content
                },
            }
        act = compose_mail_obj._get_model_action_dict().get(data['model'], '')
        if template.sans_header:
            act += '_sehead'
        elif template.sans_add:
            act += '_se'
        report = report_obj.render_report(model._ids, act, data)[0]
        return report

    @route(['/courrier/<courrierid>/<model>/<modelids>'], type='http', auth='user', website=False)
    def get_courrier(self, **kwargs):
        """
        URL permettant de renvoyer une action de téléchargement
        :param kwargs: Dictionnaire contenant les valeurs présentes dans la route
        :return: Action de téléchargement du pdf générer
        """
        if not isinstance(kwargs, dict):
            return
        template_id = int(kwargs['courrierid'])
        if not template_id:
            return False
        model_ids = [int(id_str) for id_str in kwargs['modelids'].split(',')]
        models = request.env[kwargs['model']].browse(model_ids)
        template = request.env['of.mail.template'].browse(template_id)
        all_files = []
        for model in models:
            if template.file:
                generated_file = self.print_acrobat(template, model)
            else:
                generated_file = self.print_report(template, model)
            all_files.append(generated_file)
        if len(all_files) > 1:
            """ """
            temp_file = all_files.pop()
            fd, order_pdf = tempfile.mkstemp()
            os.write(fd, temp_file)
            os.close(fd)
            file_paths = [order_pdf]

            for mail_data in all_files:
                fd, mail_pdf = tempfile.mkstemp()
                os.write(fd, mail_data)
                os.close(fd)
                file_paths.append(mail_pdf)

            result_file_path = request.env['report']._merge_pdf(file_paths)
            try:
                result_file = file(result_file_path, "rb")
                generated_file = result_file.read()
                result_file.close()
                for file_path in file_paths:
                    os.remove(file_path)
                os.remove(result_file_path)
            except Exception:
                pass

        pdfhttpheaders = [('Content-Type', 'application/pdf'), ('Content-Length', len(generated_file))]
        response = request.make_response(generated_file, headers=pdfhttpheaders)
        filename = "%s.%s" % (template.name, "pdf")
        response.headers.add('Content-Disposition', content_disposition(filename))

        return response
