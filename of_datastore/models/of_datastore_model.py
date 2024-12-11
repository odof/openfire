# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import api, fields, models

from .of_datastore_cache import DS_CACHE

# 100.000.000 ids devraient suffire pour les produits. Les chiffres suivants serviront pour le fournisseur
DATASTORE_IND = 100000000


false_value_dict = {
    "boolean": False,
    "integer": 0,
    "char": "",
    "float": 0.0,
    "text": "",
    "html": "",
    "date": False,
    "datetime": False,
    "binary": False,
    "image": False,
    "selection": "",
    "one2many": [],
    "many2many": [],
    "many2one": False,
}


class OFDatastoreModel(models.AbstractModel):
    _name = "of.datastore.model"
    _description = "OF Model Datastore"

    of_datastore_res_id = fields.Integer(string="ID on supplier database", index=True, copy=False)
    is_of_ds_search = fields.Boolean(string="IS DS Search")  # petit hack pour gérer la recherche sur les datastores
    of_datastore_is_connected = fields.Boolean(string="Is Connected", compute="_compute_of_datastore_is_connected")

    # -------------------------------------------------------------------------
    # Compute methods
    # -------------------------------------------------------------------------

    def _compute_of_datastore_is_connected(self):
        for record in self:
            record.of_datastore_is_connected = record.of_datastore_res_id > 0

    # -------------------------------------------------------------------------
    # ORM methods
    # -------------------------------------------------------------------------

    def _register_hook(self):
        # First, clear the cache for this database
        DS_CACHE.clear_cache(self.env.cr.dbname)

    def _read_from_cache(self, field_names, ids):
        ds_cache = DS_CACHE.get_cache(self.env.cr.dbname)
        # ici, tous les champs sont dans le cache, donc on va les chercher pour chaque id dans ids
        res = []
        for id_ in ids:
            value = {}
            record = self.browse(id_)
            for field_name in field_names:
                field = record._fields.get(field_name)
                try:
                    value[field_name] = field.convert_to_read(
                        field.convert_to_record(
                            ds_cache.get(record, field, false_value_dict.get(field.type, False)), record
                        ),
                        record,
                        use_name_get=False,
                    )
                except Exception:
                    value[field_name] = False

            self.push_record_ds_cache_to_cache(record, field_names)

            res.append(value)
        return res

    def _read_prefetch(self, ids):
        if not ids:
            return

        ds_cache = DS_CACHE.get_cache(self.env.cr.dbname)

        fields_to_fetch = self.of_ds_fields_to_fetch()
        fields_not_to_fetch = self.of_ds_fields_to_not_fetch()
        fields_to_calculate = self.of_ds_fields_to_calculate()

        # Il faut retirer dans fields_to_fetch les champs de fields_not_to_fetch
        fields_to_fetch = list(set(fields_to_fetch) - set(fields_not_to_fetch))
        # on va trier par base les recherches
        res_base = {}
        for id_ in ids:
            base_id = -id_ // DATASTORE_IND
            record_id = -id_ % DATASTORE_IND
            if base_id in res_base:
                res_base[base_id].append(record_id)
            else:
                res_base[base_id] = [record_id]

        datastore_supplier_obj = self.env["of.datastore.supplier"]
        for key in res_base:
            base = datastore_supplier_obj.browse(key)
            ds_res = self.of_ds_read(base, res_base[key], fields_to_fetch, load=None, check_fields=True)
            ds_res = self.of_ds_set_calculate_values(ds_res, base)

        # on ajoute des valeurs vides aux champs dont on ne veut pas les données
        for id_ in ids:
            record = self.browse(ids[0])
            for field in fields_not_to_fetch:
                if f := record._fields.get(field):
                    ds_cache.set(record, f, f.convert_to_cache(False, record, validate=True), check_dirty=False)

            self.push_record_ds_cache_to_cache(
                record, list(set(fields_to_fetch + fields_not_to_fetch + fields_to_calculate))
            )
            # on précise ici au ds_cache que ce model/id est prefetch
            DS_CACHE.set_prefetch(self.env.cr.dbname, self._name, id_)

    def _read(self, field_names):
        positive_ids = [i for i in self._ids if i > 0]
        negative_ids = [i for i in self._ids if i < 0]

        res = super(OFDatastoreModel, self.browse(positive_ids))._read(field_names) or []  # _read() peut renvoyer None

        # on va lancer le prefetch des données qui ne sont pas locales
        # uniquement pour les id qui sont pas déjà prefetch dans le ds_cache
        to_prefetch = []

        to_prefetch.extend(id_ for id_ in negative_ids if not DS_CACHE.is_prefetch(self.env.cr.dbname, self._name, id_))
        self._read_prefetch(to_prefetch)

        # quand on est ici, toutes les données dites prefetch sont dans le ds_cache
        # il ne reste donc qu'à chercher les fields qui ne sont pas prefetch
        fields_to_fetch = self.of_ds_fields_to_fetch()
        fields_not_to_fetch = self.of_ds_fields_to_not_fetch()

        fields_in_cache = list(set(fields_to_fetch + fields_not_to_fetch))

        fields_to_read = []
        fields_to_force_read = self.of_ds_fields_to_force_read()

        # TODO ? Voir si on regarde aussi à cet endroit là si la donnée est dans le cache
        # en principe, si elle est dans le cache, elle ne devrait pas être demandée ici
        fields_to_read.extend(field_name for field_name in field_names if field_name not in fields_in_cache)
        field_names = list(set(list(field_names) + fields_to_force_read))

        if not fields_to_read:
            # on doit retourner ici les champs demandés en les prenant dans le cache
            # avec ceux fait dans la fonction "normale"
            if negative_ids:
                res += self._read_from_cache(field_names, negative_ids)
            return res

        # on va trier par base les recherches
        res_base = {}
        for id_ in negative_ids:
            base_id = -id_ // DATASTORE_IND
            record_id = -id_ % DATASTORE_IND
            if base_id in res_base:
                res_base[base_id].append(record_id)
            else:
                res_base[base_id] = [record_id]

        # on ajoute les champs que l'on veut toujours avoir dans la réponse du _read

        field_names = list(set(field_names + fields_to_force_read))

        for key in res_base:
            base = self.env["of.datastore.supplier"].browse(key)
            if ds_res := self.of_ds_read(base, res_base[key], field_names, load=None, check_fields=True):
                res += ds_res

        for id_ in negative_ids:
            record = super().browse(id_)
            self.push_record_ds_cache_to_cache(record, field_names)
        return res

    # -------------------------------------------------------------------------
    # Datastore methods
    # -------------------------------------------------------------------------

    def of_ds_fields_to_fetch(self):
        if len(self.ids) <= 0:
            return []
        record = self.browse(self.ids[0])
        # les champs dont on veut les données par défaut, on retourne tous les champs avec prefetch à True
        return [field.name for field in record._fields.values() if field.prefetch]

    def of_ds_fields_to_force_read(self):
        # les champs qui doivent être retourné dans le read à chaque appels uniquement depuis le `ds_cache`
        return []

    def of_ds_fields_to_not_fetch(self):
        # les champs dont on ne veut pas les données
        return []

    def of_ds_fields_to_calculate(self):
        return []

    def of_ds_set_calculate_values(self, list_res, base):
        # on mets à jour chaque ligne avec des valeurs par défaut attention, chaque méthode super devra mettre à jour
        # le `ds_cache` et le cache odoo
        return list_res

    def of_ds_fields_to_import(self):
        ds_cache = DS_CACHE.get_cache(self.env.cr.dbname)
        record = self.browse(self.id)
        to_fetch = self.of_ds_fields_to_fetch()
        to_not_fetch = self.of_ds_fields_to_not_fetch()
        fields = ds_cache.get_fields(record)
        in_cache = [field.name for field in fields]
        return list(set(to_fetch + to_not_fetch + in_cache))

    @api.model
    def of_ds_name_search(self, base, name="", args=None, operator="ilike", limit=100):
        """
        On lance un name_search sur la base "base" distante
        """
        ds = base.of_datastore_connect()
        ds_obj = base.of_datastore_get_model(ds, self._name)
        res = base.of_datastore_name_search(ds_obj, name, args, operator, limit)
        # on va passer l'id de retour en négatif et * id de la base
        base_index = base.id * DATASTORE_IND
        for data in res:
            data[0] = -(data[0] + base_index)
        return res

    @api.model
    def of_ds_search(self, base, args, offset, limit, order, count):
        ds = base.of_datastore_connect()
        ds_obj = base.of_datastore_get_model(ds, self._name)
        return base.of_datastore_search(ds_obj, args, offset, limit, order, count)

    @api.model
    def of_ds_read(self, base, ids, fields, load=None, check_fields=False, no_cache=False):
        ds_cache = DS_CACHE.get_cache(self.env.cr.dbname)
        res = []
        base_index = base.id * DATASTORE_IND
        # on enlève les doublons potentiels
        fields = list(set(fields))

        if check_fields:
            if no_cache:
                ds = base.of_datastore_connect()
                ds_obj = base.of_datastore_get_model(ds, self._name)
                ds_fields = list(ds_obj._columns.keys())
            elif columns := DS_CACHE.get_column(self.env.cr.dbname, self._name):
                ds_fields = columns
            else:
                ds = base.of_datastore_connect()
                ds_obj = base.of_datastore_get_model(ds, self._name)
                ds_fields = list(ds_obj._columns.keys())
                # pour éviter les appels en continue à la base distante pour avoir les colonnes de l'objet, on le
                # sauvegarde dans notre cache
                DS_CACHE.set_column(self.env.cr.dbname, self._name, ds_fields)

            fields = [f for f in fields if f in ds_fields]

        if "id" not in fields:
            fields.append("id")

        if no_cache:
            new_ids = ids
            old_ids = []
        else:
            # on filtre d'abord les ids dont on a déjà les données dans le cache
            new_ids, old_ids = self.of_ds_filter_ids_in_ds_cache(base, ids, fields)

        if len(new_ids) > 0:
            ds = base.of_datastore_connect()
            ds_obj = base.of_datastore_get_model(ds, self._name)
            res += base.of_datastore_read(ds_obj, new_ids, fields, load, check_fields)
            # on modifie l'id des résultats et on ajoute au cache
            for data in res:
                data["id"] = -(data["id"] + base_index)
                record = super().browse(data["id"])
                for field_name in data.keys():
                    field = record._fields.get(field_name)
                    # on va chercher le match pour chaque valeur du champs
                    value = self.of_ds_match(field, data[field_name], base_index, data)
                    data[field_name] = value
                    if field:
                        ds_cache.set(
                            record, field, field.convert_to_cache(value, record, validate=False), check_dirty=False
                        )

        for id_ in old_ids:
            value = {}
            record = super().browse(-(id_ + base_index))
            for field in fields:
                if value_field := record._fields.get(field):
                    if field == "id":
                        value["id"] = -(id_ + base_index)
                    else:
                        value[value_field.name] = value_field.convert_to_read(
                            value_field.convert_to_record(ds_cache.get(record, value_field), record),
                            record,
                        )

            res.append(value)
        return res

    def of_ds_match(self, field, value, base_index, data):
        """Match the value with the field and return the value in the local database.

        Args:
            field: Odoo field to match
            value: value to match
            base_index: Index of the remote base
            data: Record data in which the value is

        Returns:
            The value in the local database or False if the value is not found
        """
        # On va chercher en fonction du model en cours et du field comment retourner la data
        # Cela peut être juste une conversion simple ou cela peut-être une valeur locale équivalente à la valeur
        # distante
        if not field:
            return False
        if field.type in [
            "boolean",
            "integer",
            "char",
            "float",
            "text",
            "html",
            "date",
            "datetime",
            "binary",
            "image",
            "selection",
        ]:
            return value

        if field.type == "many2one":
            if value:
                obj = field.comodel_name
                return self.env[obj].of_ds_match_many2one(value, base_index, data)
            else:
                return False
        if field.type == "many2many":
            if value:
                obj = field.comodel_name
                return self.env[obj].of_ds_match_many2many(value, base_index, data)

            else:
                return []
        if field.type == "one2many":
            if value:
                obj = field.comodel_name
                return self.env[obj].of_ds_match_one2many(value, base_index, data)
            else:
                return []

        # Si le type n'est pas trouvé, on retourne une valeur fausse
        return False

    def of_ds_match_many2one(self, value, base_index, data):
        # par défaut, on retourne False cette méthode est à surcharger dans les modèles où l'on veut la donnée
        return False

    def of_ds_match_many2many(self, value, base_index, data):
        # par défaut, on retourne une liste vide cette méthode est à surcharger dans les modèles où l'on veut la donnée
        return []

    def of_ds_match_one2many(self, value, base_index, data):
        # par défaut, on retourne une liste vide cette méthode est à surcharger dans les modèles où l'on veut la donnée
        return []

    # -------------------------------------------------------------------------
    # DS Cache methods
    # -------------------------------------------------------------------------

    @api.model
    def of_ds_filter_ids_in_ds_cache(self, base, ids, fields):
        ds_cache = DS_CACHE.get_cache(self.env.cr.dbname)
        base_index = base.id * DATASTORE_IND
        res_ids = []
        old_ids = []
        for id_ in ids:
            record = super().browse(-(id_ + base_index))
            # on vérifie si tous les champs sont bien dans le cache
            for f in fields:
                field = record._fields.get(f)
                if field and field.name != "id":
                    field_cache = ds_cache._get_field_cache(record, field)
                    if record._ids[0] not in field_cache and id_ not in res_ids:
                        res_ids.append(id_)

            if id_ not in res_ids:
                old_ids.append(id_)
        return res_ids, old_ids

    @api.model
    def push_record_ds_cache_to_cache(self, record, fields):
        ds_cache = DS_CACHE.get_cache(self.env.cr.dbname)

        for f in fields:
            if field := record._fields.get(f):
                try:
                    self.env.cache.set(record, field, ds_cache.get(record, field))
                except Exception:
                    self.env.cache.set(record, field, field.convert_to_cache(False, record))
