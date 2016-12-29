# -*- coding: utf-8 -*-

from openerp import models, api
from main import MAGIC_COLUMNS_VALUES, MAGIC_COLUMNS_TABLES

class import_mail(models.AbstractModel):
    _inherit = "of.migration"

    def import_fetchmail_server(self):
        cr = self._cr

        cr.execute("SELECT id FROm fetchmail_server LIMIT 1")
        if cr.fetchall():
            raise ValueError(u"Effectuer la migration de fetchmail_server")

    def import_ir_mail_server(self):
        cr = self._cr

        # Suppression des serveurs d'email déjà existants
        cr.execute('DELETE FROM ir_mail_server')
        cr.execute("SELECT setval('ir_mail_server_id_seq', 1, 'f')")

        # Association des product_product_61 aux nouveaux product_product 9.0
        cr.execute("UPDATE ir_mail_server_61 SET id_90 = nextval('ir_mail_server_id_seq')")

        # Création des product
        fields_90 = ['smtp_encryption', 'name', 'sequence', 'smtp_port', 'smtp_host', 'smtp_pass', 'smtp_debug', 'active', 'smtp_user']

        values = {field: "tab."+field for field in fields_90}
        values.update({
            'id'    : 'tab.id_90',
            'active': "'t'",
        })
        values.update(MAGIC_COLUMNS_VALUES)

        tables = [
            ('tab', 'ir_mail_server_61', False, False, False),
        ] + MAGIC_COLUMNS_TABLES

        self.insert_values('ir.mail_server', values, tables)

    def import_mail_message(self):
        cr = self._cr

        # Import en 2 etapes, mail_message puis mail_mail

        ####      Etape 1 : Import vers mail_message      ####

        # Ajout d'une colonne de matching pour faciliter la connexion avec mail_mail
        cr.execute('ALTER TABLE "mail_message_61" ADD COLUMN "mail_message_id_90" integer')

        # Copie du champ email_bcc vers email_cc dans le cas où il aurait été rempli
        cr.execute("UPDATE mail_message_61 SET email_cc = email_bcc "
                   "WHERE email_bcc IS NOT NULL AND email_bcc != '' "
                   "  AND (email_cc IS NULL OR email_cc = '')")
        # Mise du model a NULL si vide, pour faciliter les requêtes
        cr.execute("UPDATE mail_message_61 SET model = NULL WHERE model = ''")

        # Création des mail_message
        fields_90 = ['mail_server_id', 'subject', 'parent_id', 'subtype_id', 'res_id', 'message_id',
                     'body', 'record_name', 'no_auto_thread', 'date', 'model', 'reply_to', 'author_id',
                     'message_type', 'email_from', 'website_published', 'path']

        values = {field: "tab."+field for field in fields_90}
        values.update({
            'id'               : 'tab.mail_message_id_90',
            'mail_server_id'   : 'server.id_90',
            'parent_id'        : 'NULL',
            'subtype_id'       : 'NULL',
            'res_id'           : 'res.id_90',
            'body'             : 'tab.body_text',
            'record_name'      : 'NULL', # Récupérer le name du modèle associé
            'no_auto_thread'   : "'f'",
            'author_id'        : 'user_90.partner_id',
            'message_type'     : "'email'",
            'website_published': "'t'",
            'path'             : 'NULL',
        })
        values.update(MAGIC_COLUMNS_VALUES)

        tables = [
            ('tab', 'mail_message_61', False, False, False),
            ('server', 'ir_mail_server_61', 'id', 'tab', 'mail_server_id'),
            ('user_61', 'res_users_61', 'id', 'tab', 'user_id'),
            ('user_90', 'res_users', 'id', 'user_61', 'id_90')
        ] + MAGIC_COLUMNS_TABLES

#         model_convert = {
#             'crm.helpdesk': 'project.issue',
#         }
        message = []
        where_clause = "tab.model = '%s' AND tab.mail_message_id_90 IS NOT NULL"
        skip_models = ['crm.helpdesk', 'project.issue', 'crm.lead']
        cr.execute("SELECT DISTINCT model FROM mail_message_61 WHERE model IS NOT NULL")
        for model, in cr.fetchall():
            if model in skip_models:
                continue
            if model not in self.env:
                message.append(u"Modèle '%s' non trouvé")
                continue

            # Champ res_id
            model_obj = self.env[model]
            res_table = model_obj._table + '_61'
            model_tables = tables + [('res', res_table, 'id', 'tab', 'res_id')]

            # Association des mail_message_61 aux mail_message 9.0
            cr.execute("UPDATE mail_message_61 AS tab SET mail_message_id_90 = nextval('mail_message_id_seq')"
                       "FROM %s AS res\n"
                       "WHERE res.id = tab.res_id AND tab.model = '%s' AND res.id_90 IS NOT NULL" % (res_table, model))
            self.insert_values('mail.message', values, model_tables, where_clause % model)

        # Champ record_name
        cr.execute('SELECT DISTINCT model,res_id FROM mail_message WHERE id >= (SELECT min(mail_message_id_90) FROM mail_message_61)')
        for model,res_id in cr.fetchall():
            cr.execute('UPDATE mail_message SET record_name = %s WHERE model = %s AND res_id = %s',
                       (self.env[model].browse(res_id).name_get()[0][1], model, res_id))

        # Cas où model est NULL
        cr.execute("UPDATE mail_message_61 SET mail_message_id_90 = nextval('mail_message_id_seq') WHERE model IS NULL")
        values['res_id'] = '0'
        self.insert_values('mail.message', values, tables, "tab.model IS NULL")


        ####      Etape 2 : Import vers mail_mail      ####

        # Association des mail_message_61 aux mail_message 9.0
        cr.execute("UPDATE mail_message_61 SET id_90 = nextval('mail_mail_id_seq') WHERE mail_message_id_90 IS NOT NULL")

        # Création des mail_message
        fields_90 = ['mail_message_id', 'notification', 'auto_delete', 'body_html', 'email_to', 'headers',
                     'state', 'references', 'email_cc', 'failure_reason', 'fetchmail_server_id', 'mailing_id']

        values = {field: "tab."+field for field in fields_90}
        values.update({
            'id'                 : 'tab.id_90',
            'mail_message_id'    : 'tab.mail_message_id_90',
            'notification'       : "'f'",
            'body_html'          : "COALESCE(tab.body_html, tab.body_text)",
            'failure_reason'     : 'NULL',
            'fetchmail_server_id': 'fetchmail_server.id_90', # Dans la pratique, jamais utilisé
            'mailing_id'         : 'NULL',
        })
        values.update(MAGIC_COLUMNS_VALUES)

        tables = [
            ('tab', 'mail_message_61', False, False, False),
            ('fetchmail_server', 'fetchmail_server_61', 'id', 'tab', 'fetchmail_server_id'),
        ] + MAGIC_COLUMNS_TABLES

        self.insert_values('mail.mail', values, tables, "tab.id_90 IS NOT NULL")

        # Table mail_mail_re_partner_rel
        cr.execute("INSERT INTO mail_mail_res_partner_rel(mail_mail_id,res_partner_id)\n"
                   "SELECT mail.id_90, partner.id_90\n"
                   "FROM mail_message_61 AS mail\n"
                   "INNER JOIN res_partner_61 AS partner ON partner.id = mail.partner_id\n"
                   "WHERE mail.id_90 IS NOT NULL AND partner.id_90 IS NOT NULL")

    @api.model
    def import_module_mail(self):
        return (
            'fetchmail_server',
            'ir_mail_server',
            'mail_message',
            #@todo: product_pricelist_item
        )
