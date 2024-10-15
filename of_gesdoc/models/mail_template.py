# -*- coding: utf-8 -*-

import base64

import StringIO

from odoo import _, api, fields, models

try:
    from pdfminer.pdfdocument import PDFDocument
    from pdfminer.pdfparser import PDFParser
    from pdfminer.pdftypes import resolve1
    from pdfminer.psparser import PSLiteral
    from pdfminer.utils import decode_text
except ImportError:
    PDFParser = PSLiteral = PDFDocument = resolve1 = decode_text = None

ALLOWED_MODELS = ['sale.order', 'res.partner', 'account.invoice', 'product.template' , 'crm.lead']

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

    @api.model
    def _get_allowed_models(self):
        return ALLOWED_MODELS

    @api.model
    def _get_models_domain(self):
        return [('model', 'in', self._get_allowed_models())]

    name = fields.Char(string='Nom', size=250, required=True)
    active = fields.Boolean(string=u'Actif', default=True)
    sans_add = fields.Boolean(string='Sans adresse')
    sans_header = fields.Boolean(string=u'Sans en-tête')
    body_text = fields.Text(string='Text contents', help="Plaintext version of the message (placeholders may be used here)")
    file_name = fields.Char(string='Nom du fichier', size=64)
    file = fields.Binary("Formulaire PDF", attachment=True)
    chp_ids = fields.One2many('of.gesdoc.chp', 'template_id', string='Liste des champs', copy=True)
    fillable = fields.Boolean(u"Laisser éditable", help=u"Autorise la modification du fichier pdf après téléchargement")
    note_fields = fields.Text(compute='_compute_note_fields', string='Liste des valeurs', default=_get_note_fields)
    type = fields.Selection([], string="Type de document")
    sequence = fields.Integer(string=u"Séquence", default=10)
    model_ids = fields.Many2many(
        'ir.model', string=u"Impression rapide", domain=_get_models_domain, copy=False,
        help=u"Ajoute un raccourci dans le menu \"Imprimer\"")

    def copy(self, default=None):
        default = dict(default or {})
        default['name'] = _('%s (copy)') % self.name
        res = super(OfMailTemplate, self).copy(default)
        return res

    @api.onchange('file')
    def onchange_file(self):
        chps = [(5, 0)]
        if self.file:
            pre_vals = self.chp_ids and {chp.name: chp.value_openfire for chp in self.chp_ids} or {}
            pf = StringIO.StringIO(base64.decodestring(self.file))
            parser = PDFParser(pf)
            doc = PDFDocument(parser)
            fields = resolve1(doc.catalog.get('AcroForm', {})).get('Fields', [])

            pages = resolve1(doc.catalog.get('Pages'))
            page_kids = [str(ref) for ref in pages.get('Kids')]
            # permet de récupérer la liste des fields par page
            # car dans certains cas les fields ne portent pas l'attribut P
            pk_annots = {}
            for str_ref, page in [(str(ref), resolve1(ref)) for ref in pages.get('Kids')]:
                annots = page.get('Annots')
                if isinstance(annots, list):
                    pk_annots[str_ref] = [str(a) for a in annots]
                elif isinstance(resolve1(annots), list):
                    pk_annots[str_ref] = [str(a) for a in resolve1(annots)]

            for i in fields:
                field = resolve1(i)
                page_ref = field.get('P')

                page_number = None
                if page_ref:
                    page_number = page_kids.index(str(page_ref))
                if not page_number:
                    str_i = str(i)
                    for str_page_ref, page_annots in pk_annots.iteritems():
                        if str_i in page_annots:
                            page_number = page_kids.index(str_page_ref)
                            break

                rect = field.get('Rect')
                x0 = None
                x1 = None
                y0 = None
                y1 = None

                if not rect:
                    # Si pas de rect, on va rechercher un enfant
                    # Pas sur, sur de cette strat
                    kids = field.get('Kids')
                    if kids:
                        kid = resolve1(kids[0])
                        rect = kid.get('Rect')

                if rect:
                    x0 = rect[0]
                    y0 = rect[1]
                    x1 = rect[2]
                    y1 = rect[3]

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
                    'page_number':  page_number,
                    'x0': x0,
                    'x1': x1,
                    'y0': y0,
                    'y1': y1,
                }))

        self.chp_ids = chps

    @api.model
    def create_shortcuts(self, model_ids):
        """
        Fonction permettant la création des raccourcis d'impression
        :param model_ids:
        :return:
        """
        model_obj = self.env['ir.model']
        action_report_obj = self.env['ir.actions.report.xml']
        for model_id in model_ids:
            model = model_obj.browse(model_id)
            action_report = action_report_obj.create({
                'name' : self.name,
                'report_type' : 'controller',
                'model' : model.model,
                'print_report_name' : self.name,
                'report_name' : self.name,
                'report_rml': '/courrier/%s/%s' % (self.id, model.model),
                })
            action_report.create_action()

    @api.model
    def delete_shortcuts(self, model_ids):
        model_obj = self.env['ir.model']
        action_report_obj = self.env['ir.actions.report.xml']
        for model_id in model_ids:
            model = model_obj.browse(model_id)
            report = action_report_obj.search([('model', '=', model.model), ('report_type', '=', 'controller'),
                                               ('report_rml', '=', '/courrier/%s/%s' % (self.id, model.model))])
            report.unlink()

    @api.multi
    def change_shortcuts(self, name):
        # Change le nom du raccourci
        action_report_obj = self.env['ir.actions.report.xml']
        for mail_template in self:
            reports = action_report_obj.search(
                [('report_type', '=', 'controller'),
                 ('report_rml', 'like', '/courrier/%s/' % self.id)])
            reports.write({'name': name})

    @api.model
    def create(self, vals):
        res = super(OfMailTemplate, self).create(vals)
        res.create_shortcuts(res.model_ids.ids)
        return res

    @api.multi
    def write(self, vals):
        # Pour ajouter le raccourci dans le menu "Imprimer"
        for courrier in self:
            current_models = courrier.model_ids.ids
            active_current = vals.get('active', courrier.active)
            if 'model_ids' in vals and active_current:  # En many2many_tags le code 6 est toujours envoyé.
                old_ids = set(courrier.model_ids.ids)
                new_ids = set(vals['model_ids'][0][2])
                current_models = False
                courrier.create_shortcuts(list(new_ids - old_ids))
                courrier.delete_shortcuts(list(old_ids - new_ids))
            # Si la case "Actif" du modèle de courrier a été cochée/décochée, il faut ajouter/enlever le raccourci.
            elif 'active' in vals:
                active = vals['active']
                if active and current_models:
                    courrier.create_shortcuts(current_models)
                elif not active:
                    courrier.delete_shortcuts(courrier.model_ids.ids)
            # Si le nom du modèle de courrier change, on doit changer le nom du raccourci.
            if 'name' in vals and active_current:
                courrier.change_shortcuts(vals['name'])
        return super(OfMailTemplate, self).write(vals)

    @api.multi
    def unlink(self):
        for template in self:
            template.delete_shortcuts(template.model_ids.ids)
        return super(OfMailTemplate, self).unlink()

class OfGesdocChp(models.Model):
    _name = 'of.gesdoc.chp'
    _description = 'Champs PDF'

    name = fields.Char(string='Nom du champ PDF', required=True, readonly=True)
    value_openfire = fields.Char(string='Valeur OpenFire')
    template_id = fields.Many2one('of.mail.template', string=u'Modèle Courrier')
    to_export = fields.Boolean(string='Export', default=True)
    to_import = fields.Boolean(string='Import')
    x0 = fields.Float(string=u"Coordonnée x0 du champ")
    y0 = fields.Float(string=u"Coordonnée y0 du champ")
    x1 = fields.Float(string=u"Coordonnée x1 du champ")
    y1 = fields.Float(string=u"Coordonnée y1 du champ")
    page_number = fields.Integer(string=u"Numéro de page du champ")
