# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api, models

from .of_datastore_centralized import DATASTORE_IND


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        res_model, res_id, do_super, result = False, False, True, []
        # Build a dictionary from the domain to easily find the res_model and res_id
        domain_dict = {elem[0]: elem[2] for elem in domain if isinstance(elem, (tuple, list)) and elem[1] == "="}
        res_model = domain_dict.get("res_model")
        res_id = domain_dict.get("res_id", 0)
        res_id = int(res_id) if isinstance(res_id, str) and res_id.isdigit() else res_id

        if res_model == "product.template" and res_id:
            supplier_obj = self.env["of.datastore.supplier"]
            ds_res_id, supplier = False, None
            if res_id < 0:
                do_super = False
                supplier = supplier_obj.browse(-res_id / DATASTORE_IND)
                ds_res_id = (-res_id) % DATASTORE_IND
            else:
                product = self.env[res_model].browse(res_id)
                supplier = product.of_datastore_supplier_id
                ds_res_id = supplier and product.of_datastore_res_id or False
            if ds_res_id:
                ds_domain = [(elem[0], elem[1], ds_res_id if elem[0] == "res_id" else elem[2]) for elem in domain]
                client = supplier.of_datastore_connect()
                if not isinstance(client, str):
                    ds_attach_obj = supplier_obj.of_datastore_get_model(client, self._name)
                    result = supplier_obj.of_datastore_search_read(
                        ds_attach_obj, ds_domain, fields, offset or None, limit or None, order or None
                    )
                    supplier_value = supplier.id * DATASTORE_IND
                    for row in result:
                        row["id"] = -(supplier_value + row["id"])

        if do_super:
            result += super().search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result

    def _of_read_datastore(self, fields_to_read, create_mode=False):
        """
        Reading attachment data from external database.
        Attachments have a well-defined number of fields, which can be processed directly
        """

        supplier_obj = self.env["of.datastore.supplier"]
        result = []
        fields_defaults = {
            "create_uid": SUPERUSER_ID,
            "write_uid": SUPERUSER_ID,
            "type": "binary",
            "url": False,
            "res_id": False,
        }
        fields_defaults = [(k, v) for k, v in fields_defaults.items() if k in fields_to_read]
        datastore_fields = [field for field in fields_to_read if field not in fields_defaults]

        # Pièces jointes par fournisseur
        datastore_attachment_ids = {}
        for full_id in self._ids:
            supplier_id = -full_id / DATASTORE_IND
            datastore_attachment_ids.setdefault(supplier_id, []).append((-full_id) % DATASTORE_IND)

        for supplier_id, attachment_ids in datastore_attachment_ids.items():
            supplier_value = supplier_id * DATASTORE_IND
            if not datastore_fields:
                # Pas d'accès à la base centrale, on remplit l'id et on met tout le reste à False ou []
                datastore_defaults = {
                    field: [] if self._fields[field].type in ("one2many", "many2many") else False
                    for field in fields_to_read
                    if field != "id"
                }
                datastore_defaults |= fields_defaults
                result += [dict(datastore_defaults, id=-(att_id + supplier_value)) for att_id in attachment_ids]
                continue
            supplier = supplier_obj.browse(supplier_id)
            client = supplier.of_datastore_connect()
            ds_attachment_obj = supplier_obj.of_datastore_get_model(client, self._name)
            ds_attachment_data = supplier_obj.of_datastore_read(
                ds_attachment_obj, attachment_ids, datastore_fields, "_classic_read"
            )

            # Les champs manquants dans la table du fournisseur ne sont pas renvoyés, sans générer d'erreur
            # Il faut donc leur attribuer une valeur par défaut (False ou [] pour des one2many)
            datastore_defaults = {
                field: [] if self._fields[field].type in ("one2many", "many2many") else False
                for field in fields_to_read
                if field not in ds_attachment_data[0]
            }
            datastore_defaults |= fields_defaults

            for vals in ds_attachment_data:
                vals["id"] = -(vals["id"] + supplier_value)
                vals.update(datastore_defaults)

            result += ds_attachment_data
        return result

    def read(self, fields=None, load="_classic_read"):
        new_ids = [i for i in self._ids if i > 0]
        # Pièces jointes sur la base courante
        res = super(IrAttachment, self.browse(new_ids)).read(fields, load=load)

        if datastore_ids := [i for i in self._ids if i < 0]:
            # Si fields est vide, on récupère tous les champs accessibles pour l'objet (copié depuis BaseModel.read())
            self.check_access_rights("read")
            fields = self.check_field_access_rights("read", fields)
            res += self.browse(datastore_ids)._of_read_datastore(fields, create_mode=False)
        return res
