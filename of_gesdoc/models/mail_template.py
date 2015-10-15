# -*- coding: utf-8 -*-

import base64

# import openerp
from openerp.osv import fields, osv
from openerp.tools.translate import _
import StringIO
import os
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdftypes import resolve1
import random
import string

def random_name():
    random.seed()
    d = [random.choice(string.ascii_letters) for x in xrange(10) ]
    name = "".join(d)
    return name 
    
def create_directory(path):
    dir_name = random_name()
    path = os.path.join(path, dir_name)
    os.makedirs(path)
    return dir_name

class of_mail_template(osv.Model):
    "Templates for printing mail"
    _name = "of.mail.template"
    _description = 'Mail Templates'
    _rec_name = 'name' # override mail.message's behavior

    _columns = {
        'name'           : fields.char('Nom', size=250),
        'model_id'       : fields.many2one('ir.model', 'Modèle'),
        'user_signature' : fields.boolean('Add Signature',
                                         help="If checked, the user's signature will be appended to the text version "
                                              "of the message"),
        'report_template': fields.many2one('ir.actions.report.xml', 'Optional report to print and attach'),
        'subject'        : fields.char('Subject', size=512, required=False),
        'active'         : fields.boolean('Activée'),
        'sans_add'       : fields.boolean('Sans adresse'),
        'sans_header'    : fields.boolean('Sans en-tête'),
        'body_text'      : fields.text('Text contents', help="Plaintext version of the message (placeholders may be used here)"),
        'imp_cgv'        : fields.boolean('Ajouter dans Devis / Commande'),
        'file'           : fields.binary('Fichier PDF Formulaire'),
        'file_name'      : fields.char('Nom du fichier', size=64),
        'file_url'       : fields.char('URL du fichier', size=64),
        'file_url_dis'   : fields.related('file_url', type='char', string='URL du fichier', size=64, readonly=1),
        'chp_ids'        : fields.one2many('of.gesdoc.chp', 'template_id', 'Liste des champs'),
        'len_chp'        : fields.integer('Length'),
     }

    _defaults = {
        'active': True,
    }

    def copy(self, cr, uid, id, default=None, context=None):
        template = self.browse(cr, uid, id, context=context)
        if default is None:
            default = {}
        default = default.copy()
        default['name'] = template.name + _('(copy)')
        return super(of_mail_template, self).copy(cr, uid, id, default, context)

    def _get_file(self, cr, uid, file):
        return StringIO.StringIO(base64.decodestring(file))

    def _get_random_fname(self, path):
        flag = None
        # This can be improved
        if os.path.isdir(path):
            for dirs in os.listdir(path):
                if os.path.isdir(os.path.join(path, dirs)) and len(os.listdir(os.path.join(path, dirs))) < 4000:
                    flag = dirs
                    break
        flag = flag or create_directory(path)
        filename = random_name()
        return os.path.join(flag, filename)

    def onchange_chp(self, cr, uid, ids, chp_ids=False, len_chp=0):
        if chp_ids:
            new_len = 0
            for chp in chp_ids:
                if len(chp) >= 2:
                    if chp[0] in (2, 3):
                        raise osv.except_osv('Attention', u'Merci de rechoisir le fichier pdf pour mettre \u00E0 jour les champs')
                    elif chp[0] in (0, 1, 4, 6):
                        new_len += 1
            if new_len != len_chp:
                raise osv.except_osv('Attention', u'Merci de rechoisir le fichier pdf pour mettre \u00E0 jour les champs')
        else:
            if len_chp != 0:
                raise osv.except_osv('Attention', u'Merci de rechoisir le fichier pdf pour mettre \u00E0 jour les champs')

    def onchange_file(self, cr, uid, ids, file=False):
        chps = [(5, 0)]
        len_chp = 0
        fname = ''
        if file:
            pf = self._get_file(cr, uid, file)
            parser = PDFParser(pf)
            doc = PDFDocument(parser)
            fields = resolve1(doc.catalog['AcroForm'])['Fields']
            
            for i in fields:
                field = resolve1(i)
                name, value = field.get('T'), field.get('V')
                name = name.decode("unicode-escape", 'ignore')
                name = name.encode("utf-8")
                if value:
                    value = value.decode("unicode-escape", 'ignore')
                    value = value.encode("utf-8")
                else:
                    value = ''
                chps.append((0, 0, {
                    'name': name,
                    'value_openfire': value,
                }))
                len_chp += 1

            try:
                path = '/home/odoo/model_pdf/' + cr.dbname
                store_fname = self._get_random_fname(path)
                fname = os.path.join(path, store_fname)
                fp = open(fname, 'wb')
                file_str = base64.decodestring(file)
                try:
                    fp.write(file_str)
                finally:    
                    fp.close()
            except Exception, e:
                raise osv.except_osv(_('Erreur!'), str(e))
        return {'value': {'chp_ids': chps, 'len_chp': len_chp, 'file_url': fname, 'file_url_dis': fname}}

class of_gesdoc_chp(osv.osv):
    _name = 'of.gesdoc.chp'
    _description = 'PDF Champs'

    _columns = {
        'name': fields.char('Nom du champ PDF', size=256, required=True, readonly=True),
        'value_openfire': fields.char('Valeur OpenFire', size=256),
        'template_id': fields.many2one('of.mail.template', u'Mod\u00E9le Courrier'),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
