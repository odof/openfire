# -*- coding: utf-8 -*-

import base64
import hashlib
import mimetypes

from odoo import models, api, SUPERUSER_ID
from odoo.exceptions import AccessError
from odoo.http import request, STATIC_CACHE
from odoo.tools.mimetypes import guess_mimetype

from .of_datastore_product import DATASTORE_IND


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        # search_read est la fonction appelée par le javascript de la vue form pour récupérer les pièces jointes.
        res_model = False
        res_id = False
        do_super = True
        result = []
        for elem in domain:
            if isinstance(elem, (tuple, list)) and elem[1] == '=':
                if elem[0] == 'res_model':
                    res_model = elem[2]
                elif elem[0] == 'res_id':
                    res_id = int(elem[2])
        if res_model == 'product.template' and res_id:
            supplier_obj = self.env['of.datastore.supplier']
            ds_res_id = False
            if res_id < 0:
                do_super = False
                supplier = supplier_obj.browse(-res_id / DATASTORE_IND)
                ds_res_id = (-res_id) % DATASTORE_IND
            else:
                product = self.env[res_model].browse(res_id)
                supplier = product.of_datastore_supplier_id
                ds_res_id = supplier and product.of_datastore_res_id or False
            if ds_res_id:
                ds_domain = []
                for elem in domain:
                    if isinstance(elem, (tuple, list)) and elem[0] == 'res_id' and elem[1] == '=':
                        elem = [elem[0], elem[1], ds_res_id]
                    ds_domain.append(elem)
                client = supplier.of_datastore_connect()
                if isinstance(client, basestring):
                    # Échec de la connexion à la base fournisseur
                    # Tant pis pour les pièces jointes
                    pass
                else:
                    ds_attach_obj = supplier_obj.of_datastore_get_model(client, self._name)
                    result = supplier_obj.of_datastore_search_read(
                        ds_attach_obj, ds_domain, fields, offset or None, limit or None, order or None)
                    supplier_value = supplier.id * DATASTORE_IND
                    for row in result:
                        row['id'] = -(supplier_value + row['id'])

        if do_super:
            result += super(IrAttachment, self).search_read(
                domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result

    @api.multi
    def _of_read_datastore(self, fields_to_read, create_mode=False):
        u"""
        Lecture des données des pièces jointes sur base externe.
        Les pièces jointes ont un nombre de champs bien défini, qu'on peut traiter directement.
        """

        supplier_obj = self.env['of.datastore.supplier']
        result = []
        fields_defaults = {
            'create_uid': SUPERUSER_ID,
            'write_uid': SUPERUSER_ID,
            'type': 'binary',
            'url': False,
            'res_id': False,
        }
        fields_defaults = [(k, v) for k, v in fields_defaults.iteritems() if k in fields_to_read]
        datastore_fields = [field for field in fields_to_read if field not in fields_defaults]

        # Pièces jointes par fournisseur
        datastore_attachment_ids = {}

        for full_id in self._ids:
            supplier_id = -full_id / DATASTORE_IND
            datastore_attachment_ids.setdefault(supplier_id, []).append((-full_id) % DATASTORE_IND)

        for supplier_id, attachment_ids in datastore_attachment_ids.iteritems():
            supplier_value = supplier_id * DATASTORE_IND
            if not datastore_fields:
                # Pas d'accès à la base centrale, on remplit l'id et on met tout le reste à False ou []
                datastore_defaults = {
                    field: [] if self._fields[field].type in ('one2many', 'many2many') else False
                    for field in fields_to_read
                    if field != 'id'
                }
                datastore_defaults.update(fields_defaults)
                result += [dict(datastore_defaults, id=-(att_id + supplier_value))
                           for att_id in attachment_ids]
                continue
            supplier = supplier_obj.browse(supplier_id)
            client = supplier.of_datastore_connect()
            ds_attachment_obj = supplier_obj.of_datastore_get_model(client, self._name)

            ds_attachment_data = supplier_obj.of_datastore_read(
                ds_attachment_obj, attachment_ids, datastore_fields, '_classic_read')

            # Les champs manquants dans la table du fournisseur ne sont pas renvoyés, sans générer d'erreur
            # Il faut donc leur attribuer une valeur par défaut (False ou [] pour des one2many)
            datastore_defaults = {
                field: [] if self._fields[field].type in ('one2many', 'many2many') else False
                for field in fields_to_read
                if field not in ds_attachment_data[0]
            }
            datastore_defaults.update(fields_defaults)

            for vals in ds_attachment_data:
                vals['id'] = -(vals['id'] + supplier_value)
                vals.update(datastore_defaults)

            result += ds_attachment_data
        return result

    @api.multi
    def read(self, fields=None, load='_classic_read'):
        new_ids = [i for i in self._ids if i > 0]
        datastore_ids = [i for i in self._ids if i < 0]

        # Pièces jointes sur la base courante
        res = super(IrAttachment, self.browse(new_ids)).read(fields, load=load)

        if datastore_ids:
            # Si fields est vide, on récupère tous les champs accessibles pour l'objet (copié depuis BaseModel.read())
            self.check_access_rights('read')
            fields = self.check_field_access_rights('read', fields)
            res += self.browse(datastore_ids)._of_read_datastore(fields, create_mode=False)
        return res


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def binary_content(
            cls, xmlid=None, model='ir.attachment', id=None, field='datas', unique=False, filename=None,
            filename_field='datas_fname', download=False, mimetype=None, default_mimetype='application/octet-stream',
            env=None):
        if model != 'ir.attachment' or xmlid or not id or int(id) > 0:
            return super(IrHttp, cls).binary_content(
                xmlid=xmlid, model=model, id=id, field=field, unique=unique, filename=filename,
                filename_field=filename_field, download=download, mimetype=mimetype, default_mimetype=default_mimetype,
                env=env)
        env = env or request.env
        # get object and content

        id = int(id)
        supplier_id = -id / DATASTORE_IND
        ds_attachment_id = (-id) % DATASTORE_IND

        supplier_obj = env['of.datastore.supplier']
        supplier = supplier_obj.browse(supplier_id)
        client = supplier.of_datastore_connect()
        ds_attachment_obj = supplier_obj.of_datastore_get_model(client, model)
        datastore_fields = [field, filename_field, 'mimetype']
        datastore_fields = filter(bool, set(datastore_fields))

        # check read access
        try:
            ds_attachment_data = supplier_obj.of_datastore_read(
                ds_attachment_obj, [ds_attachment_id], datastore_fields, '_classic_read')[0]
        except AccessError:
            return 403, [], None

        status, headers, content = None, [], None

        content = ds_attachment_data[field] or ''

        # filename
        if not filename:
            if filename_field in ds_attachment_data:
                filename = ds_attachment_data[filename_field]
            else:
                filename = "%s-%s-%s" % (model, id, field)

        # mimetype
        mimetype = ds_attachment_data['mimetype'] or False
        if not mimetype:
            if filename:
                mimetype = mimetypes.guess_type(filename)[0]
            if not mimetype:
                mimetype = guess_mimetype(base64.b64decode(content), default=default_mimetype)

        headers += [('Content-Type', mimetype), ('X-Content-Type-Options', 'nosniff')]

        # cache
        etag = hasattr(request, 'httprequest') and request.httprequest.headers.get('If-None-Match')
        retag = '"%s"' % hashlib.md5(content).hexdigest()
        status = status or (304 if etag == retag else 200)
        headers.append(('ETag', retag))
        headers.append(('Cache-Control', 'max-age=%s' % (STATIC_CACHE if unique else 0)))

        # content-disposition default name
        if download:
            headers.append(('Content-Disposition', cls.content_disposition(filename)))
        return status, headers, content
