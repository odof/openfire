# -*- coding: utf-8 -*-

import base64

from openerp import models, fields, api, _

import StringIO
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdftypes import resolve1

class of_mail_template(models.Model):
    "Templates for printing mail"
    _name = "of.mail.template"
    _description = 'Mail Templates'

    name = fields.Char(string='Nom', size=250, required=True)
    active = fields.Boolean(string=u'Actif', default=True)
    sans_add = fields.Boolean(string='Sans adresse')
    sans_header = fields.Boolean(string=u'Sans en-tête')
    body_text = fields.Text(string='Text contents', help="Plaintext version of the message (placeholders may be used here)")
    file_name = fields.Char(string='Nom du fichier', size=64)
    file = fields.Binary("Formulaire PDF", attachment=True)
    chp_ids = fields.One2many('of.gesdoc.chp', 'template_id', string='Liste des champs')

    @api.one
    def copy(self, default=None):
        default = dict(default or {})
        default['name'] = _('%s (copy)') % self.name
        return super(of_mail_template, self).copy(default)

    @api.onchange('file')
    def onchange_chp_ids(self):
        chps = [(5, 0)]
        if self.file:
            pf = StringIO.StringIO(base64.decodestring(self.file))
            parser = PDFParser(pf)
            doc = PDFDocument(parser)
            fields = resolve1(doc.catalog['AcroForm'])['Fields']
            
            for i in fields:
                field = resolve1(i)
                name, value = field.get('T'), field.get('V')
                name = name.decode("unicode-escape", 'ignore').encode("utf-8")
                if value:
                    value = value.decode("unicode-escape", 'ignore').encode("utf-8")
                else:
                    value = ''
                chps.append((0, 0, {
                    'name': name,
                    'value_openfire': value,
                }))
        self.chp_ids = chps

class of_gesdoc_chp(models.Model):
    _name = 'of.gesdoc.chp'
    _description = 'Champs PDF'

    name = fields.Char(string='Nom du champ PDF', size=256, required=True, readonly=True)
    value_openfire = fields.Char(string='Valeur OpenFire', size=256)
    template_id = fields.Many2one('of.mail.template', string=u'Modèle Courrier')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
