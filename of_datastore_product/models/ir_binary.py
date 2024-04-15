# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64
import mimetypes

from odoo import _, models
from odoo.exceptions import AccessError
from odoo.http import Stream
from odoo.tools.mimetypes import guess_mimetype

from .of_datastore_centralized import DATASTORE_IND


class IrBinary(models.AbstractModel):
    _inherit = "ir.binary"

    def _find_record(self, xmlid=None, res_model="ir.attachment", res_id=None, access_token=None):
        if res_model != "ir.attachment" or xmlid or not res_id or int(res_id) > 0:
            return super()._find_record(xmlid, res_model, res_id, access_token)

        # si on a un id négatif, alors c'est bien une donnée qui vient d'une base TC
        # on va juste retourner un fake record avec l'id négatif pour que les fonctions
        # suivantes soient appelées correctement
        return {"id": res_id, "model": res_model}

    def _find_record_check_access(self, record, access_token):
        if res_id := int(record["id"]) > 0:
            return super()._find_record_check_access(record, access_token)

        model = record["model"]
        supplier_id = -res_id / DATASTORE_IND
        ds_attachment_id = (-res_id) % DATASTORE_IND

        supplier_obj = self.env["of.datastore.supplier"]
        supplier = supplier_obj.browse(supplier_id)
        client = supplier.of_datastore_connect()
        ds_attachment_obj = supplier_obj.of_datastore_get_model(client, model)

        # ici on va juste chercher si l'id existe bien, si l'accès est refusé, on lève une erreur
        try:
            supplier_obj.of_datastore_read(ds_attachment_obj, [ds_attachment_id], ["id"], "_classic_read")[0]
        except AccessError as e:
            msg = _("You can not access this Binary Field : %(error)s", error=e)
            raise AccessError(msg) from e
        return record

    def _get_stream_from(
        self,
        record,
        field_name="raw",
        filename=None,
        filename_field="name",
        mimetype=None,
        default_mimetype="application/octet-stream",
    ):
        if res_id := int(record["id"]) > 0:
            return super()._get_stream_from(record, field_name, filename, filename_field, mimetype, default_mimetype)

        model = record["model"]

        supplier_id = -res_id / DATASTORE_IND
        ds_attachment_id = (-res_id) % DATASTORE_IND

        supplier_obj = self.env["of.datastore.supplier"]
        supplier = supplier_obj.browse(supplier_id)
        client = supplier.of_datastore_connect()
        ds_attachment_obj = supplier_obj.of_datastore_get_model(client, model)

        datastore_fields = [field_name, filename_field, "mimetype", "public"]
        datastore_fields = filter(bool, set(datastore_fields))

        # ici on va juste chercher si l'id existe bien, si l'accès est refusé, on lève une erreur
        try:
            ds_attachment_data = supplier_obj.of_datastore_read(
                ds_attachment_obj, [ds_attachment_id], datastore_fields, "_classic_read"
            )[0]
        except AccessError as e:
            msg = _("You can not access this Binary Field : %(error)s", error=e)
            raise AccessError(msg) from e

        content = ds_attachment_data[field_name] or ""

        # filename
        if not filename:
            if filename_field in ds_attachment_data:
                filename = ds_attachment_data[filename_field]
            else:
                filename = f"{model}-{id}-{field_name}"

        # mimetype
        mimetype = ds_attachment_data["mimetype"] or False
        if not mimetype and filename:
            mimetype = mimetypes.guess_type(filename)[0]
        if not mimetype:
            mimetype = guess_mimetype(base64.b64decode(content), default=default_mimetype)

        return Stream(
            type="data",
            data=content,
            etag=self.env["ir.attachment"]._compute_checksum(content),
            last_modified=None,
            size=len(content),
            public=ds_attachment_data["public"],
        )
