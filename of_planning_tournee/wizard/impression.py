from osv import fields, osv
import base64
import netsvc
import os
from osv.orm import except_orm
import pypdftk



class of_imp_docs(osv.osv_memory):
    _name = 'of.imp.docs'
    _description = 'Impression Documents'
    
    def _default_doc_lines(self, cr, uid, context=None):
        planning_res_obj = self.pool['of.planning.res']
        report_xml_obj = self.pool['ir.actions.report.xml']
        pose_obj = self.pool['of.planning.pose']
        sale_order_obj = self.pool['sale.order']
        doc_line_obj = self.pool['of.imp.doc.lines']
        mail_template_obj = self.pool['mail.template']
        compose_mail_obj = self.pool['compose.mail']
        
        if context is None:
            context = {}
        planning_res_ids = context.get('active_ids', [])
        doc_line_ids = []
        if len(planning_res_ids):
            
            # les commandes, factures et poses liees avec la tournee
            res_ids_dict = {}
            pose_ids = []
            for planning_res in planning_res_obj.browse(cr, uid, planning_res_ids):
                date_pose = planning_res.date
                equipe_id = planning_res.equipe_id.id
                pose_ids = pose_obj.search(cr, uid, [('date', '>=', date_pose), ('date', '<=', date_pose), ('poseur_id', '=', equipe_id),
                                                     ('state', 'not in', ('Annule', 'Reporte'))], order='date')
            pose_vals = []
            order_vals = []
            invoice_vals = []
            if len(pose_ids):
                for pose in pose_obj.browse(cr, uid, pose_ids):
                    if [pose.id, pose.name] not in pose_vals:
                        pose_vals.append([pose.id, pose.name])
                    if pose.order_id:
                        if [pose.order_id.id, pose.order_id.name + '-' + pose.order_id.partner_id.name] not in order_vals:
                            if [pose.order_id.id, pose.order_id.name + '-' + pose.order_id.partner_id.name] not in order_vals:
                                order_vals.append([pose.order_id.id, pose.order_id.name + '-' + pose.order_id.partner_id.name])
                        if pose.order_id.invoice_ids:
                            for inv in pose.order_id.invoice_ids:
                                if [inv.id, (inv.number and (inv.number + '-') or '') + inv.partner_id.name] not in invoice_vals:
                                    if [inv.id, (inv.number and (inv.number + '-') or '') + inv.partner_id.name] not in invoice_vals:
                                        invoice_vals.append([inv.id, (inv.number and (inv.number + '-') or '') + inv.partner_id.name])
                    if pose.invoice_id:
                        if [pose.invoice_id.id, (pose.invoice_id.number and (pose.invoice_id.number + '-') or '') + pose.invoice_id.partner_id.name] \
                            not in invoice_vals:
                            invoice_vals.append([pose.invoice_id.id, (pose.invoice_id.number and (pose.invoice_id.number + '-') or '') + 
                                                 pose.invoice_id.partner_id.name])
            res_ids_dict['sale.order'] = order_vals
            res_ids_dict['account.invoice'] = invoice_vals
            res_ids_dict['of.planning.pose'] = pose_vals
            
            for res in planning_res_obj.browse(cr, uid, planning_res_ids):
                if res.docs:
                    for doc in res.docs:
                        if doc.doc_type == 'openfire':
                            report_template = doc.report_template
                            report_name = 'report.' + report_xml_obj.browse(cr, uid, report_template.id, context).report_name
                            # Ensure report is rendered using template's language
                            ctx = context.copy()
                            service = netsvc.LocalService(report_name)
                            res_vals = res_ids_dict[doc.model]
                            for r in res_vals:
                                (result, format) = service.create(cr, uid, [r[0]], {'model': doc.model}, ctx)
                                result = base64.b64encode(result)
                                ext = "." + format
                                report_file_name = str(doc.report_template.name + '_' + r[1])[:51]
                                if not report_file_name.endswith(ext):
                                    report_file_name += ext
                                line_id = doc_line_obj.create(cr, uid, {
                                                                        'doc_file': result, 
                                                                        'doc_file_name':report_file_name
                                                                        }, context=context)
                                doc_line_ids.append((4,line_id))
                        elif doc.doc_type == 'acrobat':
                            tva_template_ids = mail_template_obj.search(cr, uid, [('name', '=', 'Attestation TVA')])
                            if tva_template_ids:
                                mail_template = mail_template_obj.browse(cr, uid, tva_template_ids[0])
                                file_url = mail_template.file_url or False
                            else:
                                raise osv.except_osv('Attention', u'Il faut cr\u00E9er un mod\u00E8le de courrier Attestation TVA')
                            
                            # si le fichier pdf n'existe pas(ex: on fait la copie de la base), si le champ file existe, on recree le fichier dans le serveur
                            if not os.path.isfile(file_url):
                                if mail_template.file:
                                    try:
                                        path = '/home/openerp/model_pdf/' + cr.dbname
                                        store_fname = mail_template_obj._get_random_fname(path)
                                        file_url = os.path.join(path, store_fname)
                                        fp = open(file_url, 'wb')
                                        file_str = base64.decodestring(mail_template.file)
                                        try:
                                            fp.write(file_str)
                                        finally:    
                                            fp.close()
                                    except Exception, e:
                                        raise except_orm('Erreur!', str(e))
                                    mail_template_obj.write(cr, uid, mail_template.id, {'file_url': file_url})
                                else:
                                    raise osv.except_osv('Attention', u'Il faut ajouter un fichier pdf comme mod\u00E8le du courrier')
                                
                            datas = {}
                            data_ids = res_ids_dict[doc.model]
                            data_model = doc.model
                            for data in data_ids:
                                data_id = data[0]
                                obj = self.pool[data_model]
                                for chp in mail_template.chp_ids:
                                    lettre_data = {
                                        'ids'  : [data_id],
                                        'model': data_model,
                                        'form' : {},
                                    }
                                    datas[chp.name or ''] = chp.value_openfire and compose_mail_obj._format_lettre(cr, uid, lettre_data, chp.value_openfire, obj) or ''
                                generated_pdf = pypdftk.fill_form(file_url, datas)
                                os.rename(generated_pdf, generated_pdf + '.pdf')
                                with open(generated_pdf + '.pdf', "rb") as new_file_code:
                                    new_file = new_file_code.read()
                                    new_file_code.close()
                                report_file_name = str(doc.report_template.name + '_' + data[1])[:51] + '.pdf'
                                line_id = doc_line_obj.create(cr, uid, {
                                                                        'doc_file': base64.b64encode(new_file), 
                                                                        'doc_file_name':report_file_name
                                                                        }, context=context)
                                doc_line_ids.append((4,line_id))
                        else:
                            mail_template = doc.mail_template
                            report_name = 'report.'
                            if doc.model == 'of.planning.pose':
                                report_name += 'of_planning.'
                            else:
                                report_name += 'of_gesdoc.'
                            if doc.model == 'res.partner':
                                if mail_template.sans_add:
                                    act = 'courriers_se'
                                else:
                                    act = 'courriers'
                            elif doc.model == 'sale.order':
                                if mail_template.sans_add: 
                                    act = 'courriers_sale_se'
                                else: 
                                    act = 'courriers_sale'
                            elif doc.model == 'crm.lead':
                                if mail_template.sans_add: 
                                    act = 'courriers_crm_se'
                                else: 
                                    act = 'courriers_crm'
                            elif doc.model == 'account.invoice':
                                if mail_template.sans_add: 
                                    act = 'courriers_account_se'
                                else: 
                                    act = 'courriers_account'
                            elif doc.model == 'of.planning.pose':
                                if mail_template.sans_add: 
                                    act = 'courriers_pose_se'
                                else:
                                    act = 'courriers_pose'
                            if mail_template.sans_header: 
                                act += '_sehead'
                            report_name += act
                                
                            # Ensure report is rendered using template's language
                            ctx = context.copy()
                            service = netsvc.LocalService(report_name)
                            res_vals = res_ids_dict[doc.model]
                            for r in res_vals:
                                lettre_data = {
                                    'ids'  : [r[0]],
                                    'model': doc.model,
                                    'form' : {},
                                }
                                content = compose_mail_obj._format_lettre(cr, uid, lettre_data, mail_template.body_text or '', self.pool[doc.model])
                                (result, format) = service.create(cr, uid, [r[0]], {
                                                        'model': doc.model, 
                                                        'form': {'name': mail_template.name, 'file': False, 'file_name': '', 'file_url': '', \
                                                                 'content': content}}, ctx)
                                result = base64.b64encode(result)
                                ext = "." + format
                                report_file_name = str(doc.mail_template.name + '_' + r[1])[:51]
                                if not report_file_name.endswith(ext):
                                    report_file_name += ext
                                line_id = doc_line_obj.create(cr, uid, {
                                                                        'doc_file': result, 
                                                                        'doc_file_name':report_file_name
                                                                        }, context=context)
                                doc_line_ids.append((4,line_id))
                                                     
        return doc_line_ids
    
    _columns = {
        'doc_line_ids': fields.one2many('of.imp.doc.lines', 'doc_id', 'Lignes des documents'),
    }
    
    _rec_name = 'doc_line_ids'
    
    _defaults = {
        'doc_line_ids': _default_doc_lines,
    }
    
of_imp_docs()


class of_imp_doc_lines(osv.osv_memory):
    _name = 'of.imp.doc.lines'
    _description = 'Lignes des documents'
    
    _columns = {
        'doc_file': fields.binary('Fichier'),
        'doc_file_name': fields.char('Nom du fichier', size=64),
        'doc_id': fields.many2one('of.imp.docs', 'Document'),
    }
    
    _rec_name = 'doc_file_name'

of_imp_doc_lines()