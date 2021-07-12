# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api

# Ces champs ne doivent en aucun cas être modifiés par l'API, même si quelqu'un coche leur case 'of_api_auth'
MAGIC_AUTH_FIELDS = ["id", "create_uid", "create_date", "write_uid", "write_date", "__last_update"]


class IRModel(models.Model):
    _inherit = 'ir.model'

    of_api_auth = fields.Boolean(
        string=u"Accès API", help=u"Autoriser l'API à écrire sur les enregistrements de cet objet")


class IRModelFields(models.Model):
    _inherit = 'ir.model.fields'

    of_api_auth = fields.Boolean(
        string=u"Accès API", help=u"Autoriser l'API à écrire sur ce champ", state='manual')

    @api.multi
    def write(self, vals):
        cr = self.env.cr
        # Bypasser le verrouillage en écriture des ir_model_fields
        if len(self) == 1 and len(vals) == 1 and 'of_api_auth' in vals:
            new_val = vals['of_api_auth'] and 'true' or 'false'
            cr.execute("UPDATE ir_model_fields SET of_api_auth = %s WHERE id = %d" % (new_val, self.id))
            cr.commit()
        else:
            super(IRModelFields, self).write(vals)
        return True


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model_cr_context
    def _auto_init(self):
        # initialiser les champs d'autorisation d'accès par l'API, ne doit se déclencher qu'une fois
        cr = self._cr
        cr.execute("SELECT 1 FROM information_schema.columns "
                   "WHERE table_name = 'res_partner' AND column_name = 'of_api_create'")
        field_exists = bool(cr.fetchall())
        res = super(ResPartner, self)._auto_init()

        if not field_exists:
            cr.execute("UPDATE ir_model "
                       "SET of_api_auth = 't' "
                       "WHERE model = 'res.partner'")
            cr.execute("UPDATE ir_model_fields "
                       "SET of_api_auth = 't' "
                       "WHERE model = 'res.partner' "
                       "AND name IN ('of_accord_communication', 'of_preuve_accord_communication', 'supplier', "
                       "'customer', 'is_company', 'name', 'company_name', 'function', 'comment', 'phone', 'mobile', "
                       "'fax', 'email', 'website', 'street', 'street2', 'city', 'zip', 'geo_lat', "
                       "'geo_lng')")
        return res

    of_api_create = fields.Boolean(string=u"Création par l'API OF", readonly=True)

    @api.model
    def create(self, vals):
        # à l'installation du module, le partenaire API web est créé et l'utilisateur associé n'existe pas encore
        of_api_user = self.env.ref('of_web_api.of_api_user', raise_if_not_found=False)
        if of_api_user and self._uid == of_api_user.id:
            vals['of_api_create'] = True
        return super(ResPartner, self).create(vals)
