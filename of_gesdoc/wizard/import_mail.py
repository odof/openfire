# -*- encoding: utf-8 -*-

from odoo import models, fields, api

import StringIO
import base64
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdftypes import resolve1
from pdfminer.utils import decode_text

class OfGesdocImport(models.TransientModel):
    _name = 'of.gesdoc.import'

    template_id = fields.Many2one('of.mail.template', string=u'Modèle', required=True)
    file = fields.Binary(string=u'Fichier complété', required=True)
    file_name = fields.Char(string=u'Nom du fichier', size=64)

    @api.onchange('file')
    def onchange_file(self):
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

    def import_data_obj(self, data, obj):
        """
        @param data: dictionnaire {champ_openfire: valeur}
        @param obj: objet cible
        """

    @api.one
    def import_data(self, data):
        """
        @param data: dictionnaire {champ_openfire: valeur}
        """

    @api.multi
    def compute(self):
        pf = StringIO.StringIO(base64.decodestring(self.file))
        parser = PDFParser(pf)
        doc = PDFDocument(parser)
        fields = resolve1(doc.catalog['AcroForm'])['Fields']

        file_vals = {}
        for i in fields:
            field = resolve1(i)
            name, value = field.get('T'), field.get('V')
            name = name.decode("unicode-escape", 'ignore').encode("utf-8")
            if value:
                value = decode_text(value).encode("utf-8")
            else:
                value = ''
            file_vals[name] = value

        vals = {}
        # Recuperation des champs a importer et association {champ_openfire: valeur}
        for chp in self.template_id.chp_ids:
            if chp.to_import and chp.value_openfire and file_vals.get(chp.name):
                field = chp.value_openfire.strip()
                if field.startswith("%(") and field.endswith(")s"):
                    field = field[2:-2]
                    vals[field] = file_vals[chp.name]

        return self.import_data(vals)[0]
