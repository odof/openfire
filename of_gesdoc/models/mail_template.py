# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

import StringIO
import base64

try:
    from pdfminer.pdfparser import PDFParser
    from pdfminer.psparser import PSLiteral
    from pdfminer.pdfdocument import PDFDocument
    from pdfminer.pdftypes import resolve1
    from pdfminer.utils import decode_text
except ImportError:
    PDFParser = PSLiteral = PDFDocument = resolve1 = decode_text = None

class OfMailTemplate(models.Model):
    "Templates for printing mail"
    _name = "of.mail.template"
    _description = 'Mail Templates'
    _order = "sequence"

    @api.model
    def _get_note_fields(self):
        comp_obj = self.env['of.compose.mail']
        obj = self.env.user
        values = comp_obj._get_dict_values(obj, comp_obj._get_objects(obj))
        return "\n".join(["${%s}" % key for key in sorted(values.keys())])

    @api.multi
    def _compute_note_fields(self):
        note_fields = self._get_note_fields()
        for template in self:
            template.note_fields = note_fields

    name = fields.Char(string='Nom', size=250, required=True)
    active = fields.Boolean(string=u'Actif', default=True)
    sans_add = fields.Boolean(string='Sans adresse')
    sans_header = fields.Boolean(string=u'Sans en-tête')
    body_text = fields.Text(string='Text contents', help="Plaintext version of the message (placeholders may be used here)")
    file_name = fields.Char(string='Nom du fichier', size=64)
    file = fields.Binary("Formulaire PDF", attachment=True)
    chp_ids = fields.One2many('of.gesdoc.chp', 'template_id', string='Liste des champs')
    fillable = fields.Boolean(u"Laisser éditable", help="Autorise la modification du fichier pdf après téléchargement")
    note_fields = fields.Text(compute='_compute_note_fields', string='Liste des valeurs', default=_get_note_fields)
    type = fields.Selection([], string="Type de document")
    sequence = fields.Integer(string=u"Séquence", default=10)

    @api.one
    def copy(self, default=None):
        default = dict(default or {})
        default['name'] = _('%s (copy)') % self.name
        return super(OfMailTemplate, self).copy(default)

    @api.onchange('file')
    def onchange_file(self):
        chps = [(5, 0)]
        if self.file:
            pre_vals = self.chp_ids and {chp.name: chp.value_openfire for chp in self.chp_ids} or {}
            pf = StringIO.StringIO(base64.decodestring(self.file))
            parser = PDFParser(pf)
            doc = PDFDocument(parser)
            fields = resolve1(doc.catalog.get('AcroForm', {})).get('Fields', [])

            for i in fields:
                field = resolve1(i)
                name = field.get('T').decode("unicode-escape", 'ignore')
                value = pre_vals.get(name)
                if not value:
                    value = field.get('V')
                    if value:
                        if isinstance(value, basestring):
                            value = decode_text(value)
                        elif isinstance(value, PSLiteral):
                            value = value.name
                chps.append((0, 0, {
                    'name': name,
                    'value_openfire': value,
                    'to_export': True,
                }))
        self.chp_ids = chps

class OfGesdocChp(models.Model):
    _name = 'of.gesdoc.chp'
    _description = 'Champs PDF'

    name = fields.Char(string='Nom du champ PDF', size=256, required=True, readonly=True)
    value_openfire = fields.Char(string='Valeur OpenFire', size=256)
    template_id = fields.Many2one('of.mail.template', string=u'Modèle Courrier')
    to_export = fields.Boolean(string='Export', default=True)
    to_import = fields.Boolean(string='Import')
