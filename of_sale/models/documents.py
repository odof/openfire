# -*- coding: utf-8 -*-

import os
import base64
import tempfile
from odoo import models, fields, api

try:
    import pypdftk
except ImportError:
    pypdftk = None


class OfDocumentsJoints(models.AbstractModel):
    """ Classe abstraite qui permet d'ajouter les documents joints.
    Elle doit être surchargée pour ajouter d'autres rapports dans la fonction _allowed_reports
    et être en héritage pour la classe sur laquelle on veut ajouter la fonctionnalité.
    """
    _name = 'of.documents.joints'

    of_mail_template_ids = fields.Many2many(
        "of.mail.template", string="Documents joints",
        help=u"Intégrer des documents pdf au devis/bon de commande (exemple : CGV)"
    )

    @api.model
    def _allowed_reports(self):
        """
        Fonction qui affecte un nom de rapport à un modèle.
        Si le nom de rapport imprimé n'est pas dans la liste de clés du dictionnaire,
        alors les documents joints ne seront pas imprimés.
        :return: {'nom_du_rapport' : modèle.concerné'}
        """
        return {'sale.report_saleorder': 'sale.order', 'account.report_invoice': 'account.invoice'}

    @api.multi
    def _detect_doc_joint(self):
        """
        Cette fonction retourne les données des documents à joindre au fichier pdf du devis/commande au format binaire.
        Le document retourné correspond au fichier pdf joint au modéle de courrier.
        @todo: Permettre l'utilisation de courriers classiques et le remplissage des champs.
        :return: liste des documents à ajouter à la suite du rapport
        """
        self.ensure_one()
        compose_mail_obj = self.env['of.compose.mail']
        attachment_obj = self.env['ir.attachment']
        data = []
        force_of_mail_template_ids = self._context.get('force_of_mail_template_ids')
        if force_of_mail_template_ids:
            of_mail_template_ids = self.env['of.mail.template'].browse(force_of_mail_template_ids)
        else:
            of_mail_template_ids = self.of_mail_template_ids
        for mail_template in of_mail_template_ids:
            if mail_template.file:
                # Utilisation des documents pdf fournis
                if not mail_template.chp_ids:
                    data.append(mail_template.file)
                    continue
                # Calcul des champs remplis sur le modèle de courrier
                attachment = attachment_obj.search([('res_model', '=', mail_template._name),
                                                    ('res_field', '=', 'file'),
                                                    ('res_id', '=', mail_template.id)])
                datas = dict(compose_mail_obj.eval_champs(self, mail_template.chp_ids))
                file_path = attachment_obj._full_path(attachment.store_fname)
                fd, generated_pdf = tempfile.mkstemp(prefix='doc_joint_', suffix='.pdf')
                try:
                    pypdftk.fill_form(file_path, datas, out_file=generated_pdf, flatten=not mail_template.fillable)
                    with open(generated_pdf, "rb") as encode:
                        encoded_file = base64.b64encode(encode.read())
                finally:
                    os.close(fd)
                    try:
                        os.remove(generated_pdf)
                    except Exception:
                        pass
                data.append(encoded_file)
        return data
