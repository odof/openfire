# -*- coding: utf-8 -*-

from openerp import models, api
from main import MAGIC_COLUMNS_VALUES, MAGIC_COLUMNS_TABLES

class import_post_process(models.AbstractModel):
    _inherit = 'of.migration'

    @api.model
    def import_ir_property(self):
        """ Exceptionnellement, la colonne id_90 ne sera pas peuplée, requête pénible avec jointures, temps perdu inutile
        """
        cr = self._cr

        fields_90 = ['value_text', 'value_float', 'name', 'type', 'company_id', 'fields_id', 'value_datetime',
                     'value_binary', 'value_reference', 'value_integer', 'res_id']

        values = {field: "tab."+field for field in fields_90}
        values.update({
#             'id'        : 'tab.id_90',
            'company_id': 'comp.id_90',
            'res_id'    : 'res.id_90',
        })
        values.update(MAGIC_COLUMNS_VALUES)

        tables = [
            ('tab', 'ir_property_61', False, False, False),
            ('comp', 'res_company_61', 'id', 'tab', 'company_id'),
            ('field', 'ir_model_fields_61', 'id', 'tab', 'fields_id'),
        ] + MAGIC_COLUMNS_TABLES

        where_clauses = ('tab.fields_id = %s AND res.id_90 IS NOT NULL',
                         'tab.fields_id = %s AND res.id_90 IS NOT NULL AND ref.id_90 IS NOT NULL')

        # Récupération de tous les fields.property renseignés en 6.1
        cr.execute("SELECT f61.model, f61.name, f61.id, f90.id, f90.relation\n"
                   "FROM ir_model_fields_61 AS f61\n"
                   "LEFT JOIN ir_model_fields AS f90 ON f90.id = f61.id_90\n"
                   "WHERE f61.id IN \n"
                   "(SELECT DISTINCT fields_id FROM ir_property_61 WHERE res_id IS NOT NULL)")

        message = u""
        for model, field_name, field_id, field_id90, relation90 in cr.fetchall():
            if not field_id90:
                message += u"Propriété non trouvée en v9 : %s.%s\n" % (model, field_name)
                continue
            values['fields_id'] = str(field_id90)

            # Champ res_id
            values['res_id'] = "TEXTCAT('%s,', TEXT( res.id_90 ))" % model
            res_table = self.env[model]._table + '_61'
            prop_tables = tables + [('res', res_table, False, 'tab', "res.id = substring(tab.res_id FROM E'\\\\d*$')::int")]

            # Champ value_reference
            if relation90:
                values['value_reference'] = "TEXTCAT('%s,', TEXT( ref.id_90 ))" % relation90
                ref_table = self.env[relation90]._table + '_61'
                prop_tables.append(('ref', ref_table, False, 'tab', "ref.id = substring(tab.value_reference FROM E'\\\\d*$')::int"))
            else:
                values['value_reference'] = 'f'

            self.insert_values('ir.property', values, prop_tables, where_clauses[bool(relation90)] % field_id)
        return message

    @api.model
    def import_wkf(self):
        self.model_data_mapping('wkf_61', 'workflow')

    @api.model
    def import_wkf_instance(self):
        cr = self._cr

        # Association des wkf_instance_61 aux wkf_instance 9.0
        cr.execute("UPDATE wkf_instance_61 AS wi SET id_90 = nextval('wkf_instance_id_seq')\n"
                   "FROM wkf_61 AS wkf\n"
                   "WHERE wkf.id=wi.wkf_id AND wkf.id_90 IS NOT NULL")

        fields_90 = ['id', 'res_type', 'uid', 'wkf_id', 'state', 'res_id']

        values = {field: "tab."+field for field in fields_90}
        values.update({
            'id'    : 'tab.id_90',
            'uid'   : 'res_user.id_90',
            'res_id': 'obj.id_90',
        })

        tables = [
            ('tab', 'wkf_instance_61', False, False, False),
            ('res_user', 'res_users_61', 'id', 'tab', 'uid'),
        ]

        where_clause = "tab.wkf_id = %s AND tab.id_90 IS NOT NULL"

        cr.execute("SELECT id,id_90,osv FROM wkf_61 WHERE id_90 IS NOT NULL")
        for wkf_id, wkf_id90, model_name in cr.fetchall():
            values['wkf_id'] = str(wkf_id90)
            res_table_name = model_name.replace('.', '_') + '_61'
            tab = tables + [
                ('obj', res_table_name, 'id', 'tab', 'res_id')
            ]

            self.insert_values('workflow.instance', values, tab, where_clause % wkf_id)

    @api.model
    def import_wkf_activity(self):
        self.model_data_mapping('wkf_activity_61', 'workflow.activity')

    @api.model
    def import_wkf_workitem(self):
        cr = self._cr

        # Association des wkf_workitem_61 aux wkf_workitem 9.0
        cr.execute("UPDATE wkf_workitem_61 AS ww SET id_90 = nextval('wkf_workitem_id_seq')\n"
                   "FROM wkf_instance_61 AS wi\n"
                   "WHERE wi.id=ww.inst_id AND wi.id_90 IS NOT NULL")

        fields_90 = ['id', 'act_id', 'inst_id', 'subflow_id', 'state']

        values = {field: "tab."+field for field in fields_90}
        values.update({
            'id'        : 'tab.id_90',
            'act_id'    : 'act.id_90',
            'inst_id'   : 'inst.id_90',
            'subflow_id': 'subflow.id_90',
        })

        tables = [
            ('tab', 'wkf_workitem_61', False, False, False),
            ('act', 'wkf_activity_61', 'id', 'tab', 'act_id'),
            ('inst', 'wkf_instance_61', 'id', 'tab', 'inst_id'),
            ('subflow', 'wkf_instance_61', 'id', 'tab', 'subflow_id'),
        ]

        where_clause = "tab.id_90 IS NOT NULL"

        self.insert_values('workflow.workitem', values, tables, where_clause)

    @api.model
    def import_ir_attachment_old(self):
        """ ETAPES
        1 - Récupérer les différents fichiers 6.1
        2 - Calculer leur checksum et renseigner la table ir_attachment_61
        3 - Renommer et placer les fichiers dans le bon dossier 9.0, si non déjà existant
        4 - Migrer la table ir_attachment_61 vers ir_attachment
        """
        cr = self._cr

        cr.execute('ALTER TABLE "res_partner_bank_61" ADD COLUMN "checksum" character varying(40)')



        #@todo : Ajouter le matching des pièces jointes existantes...
        # ... il faudra choisir les objets affectés (le logo de la société est déjà migré...)

        fields_90 = ['res_model', 'res_name', 'db_datas', 'file_size', 'company_id', 'index_content', 'type', 'public',
                     'store_fname', 'description', 'res_field', 'mimetype', 'name', 'url', 'res_id', 'checksum', 'datas_fname']

        values = {field: "tab."+field for field in fields_90}
        values.update({
            'id'        : 'tab.id_90',
            'company_id': 'comp.id_90',
            'mimetype'  : 'tab.file_type',
        })

        # Mapper res_id avec res_model

        tables = [
            ('tab', 'wkf_workitem_61', False, False, False),
            ('act', 'wkf_activity_61', 'id', 'tab', 'act_id'),
            ('inst', 'wkf_instance_61', 'id', 'tab', 'inst_id'),
            ('subflow', 'wkf_instance_61', 'id', 'tab', 'subflow_id'),
        ]

    def import_ir_attachment(self):
        """ ETAPES
        1 - Migrer la table ir_attachment_61 vers ir_attachment
        2 - Pour chaque ligne migrée, récupérer le fichier 6.1 et l'enregistrer via odoo
        """

        file_path = '/home/odoo/filestore/%s/' % self._cr.dbname

        def _file_read(fname):
            r = ''
            try:
                r = open(file_path + fname,'rb').read().encode('base64')
#             except (IOError, OSError):
#                 pass
            except Exception, e:
                print 'sniiiiif'
            return r

        cr = self._cr
        attachment_obj = self.env['ir.attachment']

        fields_90 = ['res_model', 'res_name', 'db_datas', 'file_size', 'company_id', 'index_content', 'type', 'public',
                     'store_fname', 'description', 'res_field', 'mimetype', 'name', 'url', 'res_id', 'checksum', 'datas_fname']

        values = {field: "tab."+field for field in fields_90}
        values.update({
            'id'         : 'tab.id_90',
            'company_id' : 'comp.id_90',
            'mimetype'   : 'tab.file_type',
            'res_id'     : 'res.id_90',
            'public'     : "'f'",
            'store_fname': 'NULL', # Mis à NULL pour qu'Odoo ne cherche pas à supprimer le fichier
            'res_field'  : 'NULL',
            'checksum'   : 'NULL',
        })

        # Mapper res_id avec res_model

        tables = [
            ('tab', 'ir_attachment_61', False, False, False),
            ('comp', 'res_company_61', 'id', 'tab', 'company_id'),
        ] + MAGIC_COLUMNS_TABLES

        where_clause = "tab.res_model = '%s' AND tab.id_90 IS NOT NULL"

        cr.execute("SELECT DISTINCT res_model FROM ir_attachment_61")

        # ETAPE 1 : Création des lignes dans la table ir_attachment
        message = []
        skip_models = ['mail.compose.message','crm.lead']
        switch_models = {'mail.message': 'mail.mail'}
        for res_model, in cr.fetchall():
            if res_model in skip_models:
                continue
            if res_model not in self.env:
                message.append(u"Modèle '%s' non trouvé")
                continue

            # Champ res_id
            model_obj = self.env[res_model]
            res_table = model_obj._table + '_61'
            model_tables = tables + [('res', res_table, 'id', 'tab', 'res_id')]

            # Association des ir_attachment_61 aux ir_attachment 9.0
            cr.execute("UPDATE ir_attachment_61 AS tab SET id_90 = nextval('ir_attachment_id_seq')\n"
                       "FROM %s AS res\n"
                       "WHERE res.id = tab.res_id AND tab.res_model = '%s' AND res.id_90 IS NOT NULL" % (res_table, res_model))

            values['res_model'] = "'%s'" % switch_models.get(res_model, res_model)
            self.insert_values('ir.attachment', values, model_tables, where_clause % res_model)

        # ETAPE 2 : Migration du fichier et mise à jour des valeurs
        missed_count = 0
        cr.execute("SELECT id_90,store_fname FROM ir_attachment_61 WHERE id_90 IS NOT NULL AND store_fname IS NOT NULL")
        for id_90, path in cr.fetchall():
            data = _file_read(path)
            if not data:
                missed_count += 1
                continue

            cr.execute("SELECT id FROM ir_attachment WHERE id = %s" % id_90)
            print id_90, cr.fetchall()

            attachment_obj.browse(id_90).datas = data
        if missed_count:
            message.append("%s fichier(s) non trouvé(s)" % missed_count)

        # Table message_attachment_rel
        cr.execute("INSERT INTO message_attachment_rel(message_id, attachment_id)\n"
                   "SELECT message.mail_message_id_90, attachment.id_90\n"
                   "FROM message_attachment_rel_61 AS tab\n"
                   "INNER JOIN mail_message_61 AS message ON message.id = tab.message_id\n"
                   "INNER JOIN ir_attachment_61 AS attachment ON attachment.id = tab.attachment_id\n"
                   "WHERE message.mail_message_id_90 IS NOT NULL\n"
                   "  AND attachment.id_90 IS NOT NULL")

        return "\n".join(message)

    @api.model
    def import_module_post_process(self):
        return (
            'ir_property',
            'wkf',
            'wkf_instance',
            'wkf_activity',
            'wkf_workitem',
            'ir_attachment',
        )
