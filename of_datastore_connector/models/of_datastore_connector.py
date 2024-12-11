# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from urllib.parse import urlparse

from odoo import _, api, fields, models
from odoo.exceptions import UserError

DATASTORE_IND = 100000000

_logger = logging.getLogger(__name__)

try:
    import odoorpc
except (ImportError, IOError) as err:
    _logger.debug(err)


class OFDatastoreConnector(models.AbstractModel):
    """
    Fonctions de communication avec le serveur.
    Toute communication distante doit se faire par appel de ces fonctions.
    Le changement d'outil de connexion (erppeek, openerplib, odoorpc) peut ainsi se faire par "simple"
        redéfinition des méthodes de cette classe.
    """

    _name = "of.datastore.connector"
    _description = "Datastore Connector"
    _rec_name = "db_name"
    _order = "db_name"

    server_address = fields.Char(string="Server address", required=True)
    db_name = fields.Char(string="Database", required=True)
    login = fields.Char(required=True)
    password = fields.Char()
    new_password = fields.Char(
        string="Set Password",
        compute="_compute_new_password",
        inverse="_inverse_new_password",
        help="Specify a value only when changing the password, otherwise leave empty",
    )
    error_msg = fields.Char(string="Error", compute="_compute_error_msg")
    active = fields.Boolean(default=True)

    _sql_constraints = [("db_name_uniq", "unique (db_name)", "There is already a connection to this database")]

    # -------------------------------------------------------------------------
    # Compute methods
    # -------------------------------------------------------------------------

    @api.depends()
    def _compute_new_password(self):
        for connector in self:
            connector.new_password = ""  # nosec B105:hardcoded_password_string

    def _inverse_new_password(self):
        """Method copied from `res_users._set_new_password`"""
        for connector in self:
            if not connector.new_password:
                # Do not update the password if no value is provided, ignore silently.
                # For example web client submits False values for all empty fields.
                continue
            connector.password = connector.new_password

    @api.depends("db_name", "server_address", "login", "password", "new_password")
    def _compute_error_msg(self):
        for connector in self:
            for field_name in ("db_name", "server_address", "login", "password", "new_password"):
                if field_name == "new_password" and connector.password:
                    # Le nouveau mot de passe n'est obligatoire que s'il n'en existe pas déjà un
                    continue
                if not connector[field_name]:
                    error_msg = (
                        _('You must fill the field "%s"')
                        % self.env["ir.model.fields"]
                        .search([("model", "=", self._name), ("name", "=", field_name)])
                        .name_get()[0][1]
                    )
                    break
            else:
                error_msg = connector.of_datastore_connect()
                if not isinstance(error_msg, str):
                    error_msg = _("Connection successful")
            connector.error_msg = error_msg

    # -------------------------------------------------------------------------
    # Onchange methods
    # -------------------------------------------------------------------------

    @api.onchange("server_address")
    def onchange_server_address(self):
        if self.server_address and not self.server_address.startswith("http"):
            return {"value": {"server_address": f"https://{self.server_address}"}}  # noqa
        return False

    @api.onchange("db_name")
    def onchange_db_name(self):
        if self.db_name:
            return {"value": {"server_address": f"https://{self.db_name}.openfire.fr"}}  # noqa
        return False

    @api.model
    def _get_context(self):
        return {key: val for key, val in self._context.copy().items() if key in ("lang", "tz", "active_test")}

    @api.model
    def get_connector(self, url, db_name, login, password):
        # Connexion à la base du fournisseur
        try:
            parse_url = urlparse(url)
            port = parse_url.port or 80

            protocol = "jsonrpc+ssl" if port == 443 else "jsonrpc"
            odoo_tc = odoorpc.ODOO(host=parse_url.hostname, port=port, protocol=protocol, timeout=120)

            odoo_tc.login(db=db_name, login=login, password=password)

            # Opération pour vérifier la connexion
            odoo_tc.env["res.users"].search([], limit=1)
            return odoo_tc
        except Exception as exc:
            raise UserError(_(str(exc)))

    def of_datastore_connect(self):
        self.ensure_one()
        # Call sudo() as no user shall have access right to this object
        connector = self.sudo()

        return self.get_connector(
            connector.server_address, connector.db_name, connector.login, connector.new_password or connector.password
        )

    @api.model
    def of_datastore_get_model(self, ds_client, model_name):
        return ds_client.env[model_name]

    @api.model
    def of_datastore_search(self, ds_model, args, offset=None, limit=None, order=None, count=None):
        kwargs = {
            key: val
            for key, val in [
                ("offset", offset),
                ("limit", limit),
                ("order", order),
                ("count", count),
            ]
            if val is not None
        }

        return ds_model.with_context(self._get_context()).search(args, **kwargs)

    @api.model
    def of_datastore_name_search(self, ds_model, name=None, args=None, operator=None, limit=None):
        kwargs = {
            key: val
            for key, val in [
                ("name", name),
                ("args", args),
                ("operator", operator),
                ("limit", limit),
            ]
            if val is not None
        }

        return ds_model.with_context(self._get_context()).name_search(**kwargs)

    @api.model
    def of_datastore_name_get(self, ds_model, ids):
        return ds_model.name_get(ids)

    @api.model
    def of_datastore_read(self, ds_model, ids, fields=None, load=None, check_fields=False):
        if check_fields:
            ds_fields = list(self.env[ds_model._name]._fields)
            fields = [f for f in fields if f in ds_fields]

        kwargs = {key: val for key, val in [("fields", fields), ("load", load)] if val is not None}

        return ds_model.with_context(self._get_context()).read(ids, **kwargs)

    @api.model
    def of_datastore_read_group(
        self, ds_model, domain, fields, groupby, offset=None, limit=None, orderby=None, lazy=None
    ):
        kwargs = {
            key: val
            for key, val in [
                ("offset", offset),
                ("limit", limit),
                ("orderby", orderby),
                ("lazy", lazy),
            ]
            if val is not None
        }
        return ds_model.with_context(self._get_context()).read_group(domain, fields, groupby, **kwargs)

    @api.model
    def of_datastore_search_read(self, ds_model, domain=None, fields=None, offset=0, limit=None, order=None):
        return ds_model.search_read(domain, offset, limit, order, count=False)

    @api.model
    def of_datastore_create(self, ds_model, values):
        kwargs = {"context": self._get_context()}
        return ds_model.create(values, **kwargs)

    @api.model
    def of_datastore_write(self, ds_model, ids, values):
        kwargs = {"context": self._get_context()}
        return ds_model.write(ids, values, **kwargs)

    @api.model
    def of_datastore_func(self, ds_model, func, params, optional_params):
        kwargs = {key: val for key, val in optional_params if val is not None}
        kwargs["context"] = self._get_context()
        args = tuple(params)
        return getattr(ds_model, func)(*args, **kwargs)
