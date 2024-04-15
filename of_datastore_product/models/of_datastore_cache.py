# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from contextlib import contextmanager, suppress
from threading import Lock

from odoo import api, fields, models, registry
from odoo.tools.safe_eval import safe_eval

from odoo.addons.of_utils.models.bigint import BigInteger


class OFDatastoreCache(models.TransientModel):
    """
    This transient model manages caching of data retrieved from a central datastore.
    It provides methods to store and retrieve cached values for specific models and records.
    Caching helps reduce the load on the central datastore by storing frequently accessed data locally.

    Args:
        _datastore_cache_locks: A dictionary to manage locks for thread-safe access to cached data.

    Methods:
        - _get_cache_token: A context manager to acquire and release a lock for accessing cached data.
        - _get_company: Retrieves the company associated with the current user.
        - store_values: Updates or creates cache entries for the provided model and values.
        - apply_values: Applies cached values to the provided record.
    """

    _name = "of.datastore.cache"
    _description = "Datastore Cache"
    _datastore_cache_locks = {"main": Lock()}

    model = fields.Char(required=True, help="The name of the Odoo model for which data is cached.")
    res_id = BigInteger(string="Resource id", required=True, help="The ID of the resource for which data is cached.")
    company_id = fields.Many2one(
        comodel_name="res.company", string="Company", required=True, help="The company associated with the cached data."
    )
    vals = fields.Char(
        string="Values", help="A dictionary representing the cached values for the object.", required=True
    )

    @contextmanager
    def _get_cache_token(self, key, blocking=True):
        """
        Token function to prevent different threads from simultaneously accessing the same key.
        So, if several threads want to retrieve the same data on a central basis,
        only the first one will be allowed to do so while the others wait for the result.

        Args:
            key (str) : Key used to identify a token (in practice this is the ID of the connector at the central base).
            blocking (boolean) : If True, the process will wait until the token is released.
                If False, the function will return False if the token is not available.

        Returns:
            The 'of.datastore.cache' model with a new cursor if the token could be obtained, False otherwise.
        """
        if key not in self._datastore_cache_locks:
            self._datastore_cache_locks["main"].acquire()
            if key not in self._datastore_cache_locks:
                self._datastore_cache_locks[key] = Lock()
            self._datastore_cache_locks["main"].release()

        acquired = self._datastore_cache_locks[key].acquire(blocking)
        try:
            if acquired:
                cr = registry(self._cr.dbname).cursor()
                result = self.env(cr=cr)["of.datastore.cache"]
            yield result
            cr.commit()
        finally:
            if acquired:
                with suppress(Exception):
                    cr.close()
                self._datastore_cache_locks[key].release()

    def _get_company(self):
        company = self.env.user.company_id
        # TODO: Move this to a separate module with an inherit of this method ?
        if hasattr(company, "accounting_company_id"):
            # Utilisation de la société comptable si le module of_base_multicompany est installé
            company = company.accounting_company_id

    @api.model
    def store_values(self, model, vals):
        """Cache update function.
        This function should never be called without first acquiring a token with _get_cache_token
        """
        model_obj = self.env[model]
        res_ids = [v["id"] for v in vals]
        company = self._get_company()
        stored = {
            ds_cache.res_id: ds_cache
            for ds_cache in self.search(
                [("model", "=", model), ("company_id", "=", company.id), ("res_id", "in", res_ids)]
            )
        }
        for v in vals:
            # Les champs calculés ne doivent pas être stockés
            v = {key: val for key, val in v.items() if not model_obj._of_datastore_is_computed_field(key)}
            ds_cache = stored.get(v["id"])
            v = model_obj._convert_to_cache(v, update=True, validate=False)
            res_id = v.pop("id")
            if ds_cache:
                ds_cache_vals = safe_eval(ds_cache.vals)
                ds_cache_vals.update(v)
                # Appel explicite de write, une affectation avec '=' ne marcherait pas si on est dans un on_change
                ds_cache.write({"vals": str(ds_cache_vals)})
            else:
                self.create(
                    {
                        "model": model,
                        "res_id": res_id,
                        "company_id": company.id,
                        "vals": str(v),
                    }
                )

    @api.model
    def apply_values(self, record):
        """
        Apply the values from the cache to the given record.

        Args:
            record (Record): The record to apply the values to.

        Returns:
            None
        """
        record.ensure_one()

        # New cursor to retrieve data from the DB independently of this process.
        # Essential since `store_values()` is applied on a separate cursor, generated by `_get_cache_token()`.
        with registry(self._cr.dbname).cursor() as cr:
            company = self._get_company()

            cr.execute(  # Performance choice: we don't use the ORM to avoid the cache
                "SELECT vals FROM of_datastore_cache WHERE model = %s AND company_id = %s AND res_id = %s",
                (record._name, company.id, record.id),
            )
            if vals := cr.fetchall():
                vals = safe_eval(vals[0][0])
                record._cache.update(record._convert_to_cache(vals, validate=False))
