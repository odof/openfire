# -*- coding: utf-8 -*-
import logging
import threading
import xmlrpclib
import socket  # Ne pas supprimer cette ligne, voir fonction connect()

from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)

try:
    import openerplib  # sudo easy_install openerp-client-lib
except (ImportError, IOError) as err:
    _logger.debug(err)


class OfDatastoreConnector(models.AbstractModel):
    u"""
    Fonctions de communication avec le serveur.
    Toute communication distante doit se faire par appel de ces fonctions.
    Le changement d'outil de connexion (erppeek, openerplib, odoorpc) peut ainsi se faire par "simple"
        redéfinition des méthodes de cette classe.
    """
    _name = 'of.datastore.connector'

    server_address = fields.Char(string=u'Server address', required=True)
    db_name = fields.Char(u'Database', required=True)
    login = fields.Char('Login', required=True)
    password = fields.Char('Password')
    new_password = fields.Char(
        string='Set Password', compute='_compute_new_password', inverse='_inverse_new_password',
        help="Specify a value only when changing the password, otherwise leave empty")
    error_msg = fields.Char(string='Error', compute='_compute_error_msg')

    @api.depends()
    def _compute_new_password(self):
        for supplier in self:
            supplier.new_password = ''

    # Fonctions récupérées depuis le champ new_password défini pour res_users.
    def _inverse_new_password(self):
        for supplier in self:
            if not supplier.new_password:
                # Do not update the password if no value is provided, ignore silently.
                # For example web client submits False values for all empty fields.
                continue
            supplier.password = supplier.new_password

    @api.depends('db_name', 'server_address', 'login', 'password', 'new_password')
    def _compute_error_msg(self):
        for connector in self:
            for field_name in ('db_name', 'server_address', 'login', 'password', 'new_password'):
                if field_name == 'new_password' and connector.password:
                    # Le nouveau mot de passe n'est obligatoire que s'il n'en existe pas déjà un
                    continue
                if not connector[field_name]:
                    error_msg = _("You must fill the field \"%s\"") % self.env['ir.model.fields'].search(
                        [('model', '=', self._name), ('name', '=', field_name)]).name_get()[0][1]
                    break
            else:
                error_msg = connector.of_datastore_connect()
                if not isinstance(error_msg, basestring):
                    error_msg = _('Connection successful')
            connector.error_msg = error_msg

    @api.model
    def _get_context(self):
        return {key: val for key, val in self._context.iteritems() if key in ('lang', 'tz', 'active_test')}

    @api.multi
    def of_datastore_connect(self):
        # Connexion à la base du fournisseur
        # Utilisation d'un thread pour stopper une connexion trop longue
        class FuncThread(threading.Thread):
            def __init__(self):
                threading.Thread.__init__(self)
                self.result = None

            def run(self):
                try:
                    server_address = supplier.server_address
                    # ========== Code à recommenter après la résolution du bug OVH ==========
                    # Retrait du prefixe http:// et extraction du port (optionnel)
                    address_split = server_address.split('://')[-1].split(':')  # [adresse, port]
                    ip_address = socket.gethostbyname(address_split[0])
                    if len(address_split) == 2:
                        port = ':' + address_split[1]
                    elif ip_address == socket.gethostbyname('s-alpha.openfire.fr'):
                        # Sur s-alpha le port 8010 est utilisé pour la connexion xmlrpc v10
                        port = ':8010'
                    else:
                        port = ''
                    server_address = "http://%s%s" % (ip_address, port)
                    # =======================================================================

                    i = server_address.find('://')
                    if i == -1:
                        # Protocole xmlrpcs par defaut
                        protocol = 'xmlrpcs'
                        address = server_address
                    else:
                        # Protocole xmlrpc ou xmlrpcs en fonction de http ou https
                        protocol = server_address[:i].replace('http', 'xmlrpc')
                        address = server_address[i+3:]
                    j = address.find(':')
                    if j == -1:
                        port = 443 if server_address[:i] == 'https' else 80
                    else:
                        port = int(address[j+1:])
                        address = address[:j]
                    cli = openerplib.get_connection(hostname=address, port=port, protocol=protocol,
                                                    database=supplier.db_name,
                                                    login=supplier.login, password=supplier.new_password or supplier.password)

                    # Opération pour vérifier la connexion
                    self.result = cli.get_model('res.users').search([]) and cli or ''
                except xmlrpclib.Fault, exc:
                    self.result = exc.faultCode
                except Exception, exc:
                    self.result = _(str(exc))
        self.ensure_one()
        # Call super() as no user shall have access right to this object
        supplier = self.sudo()

        it = FuncThread()
        it.start()
        it.join(10)  # attente de 10 secondes ou jusqu'à la fin de l'opération
        if it.isAlive():
            client = _('Connection timeout')
        else:
            client = it.result
        return client

    @api.model
    def of_datastore_get_model(self, ds_client, model_name):
        return ds_client.get_model(model_name)

    @api.model
    def of_datastore_search(self, ds_model, args, offset=None, limit=None, order=None, count=None):
        kwargs = {
            key: val
            for key, val in [('offset', offset),
                             ('limit', limit),
                             ('order', order),
                             ('count', count),
                             ('context', self._get_context())]
            if val is not None}
        return ds_model.search(args, **kwargs)

    @api.model
    def of_datastore_name_search(self, ds_model, name=None, args=None, operator=None, limit=None):
        kwargs = {
            key: val
            for key, val in [('name', name),
                             ('args', args),
                             ('operator', operator),
                             ('limit', limit),
                             ('context', self._get_context())]
            if val is not None}
        return ds_model.name_search(**kwargs)

    @api.model
    def of_datastore_name_get(self, ds_model, ids):
        return ds_model.name_get(ids)

    @api.model
    def of_datastore_read(self, ds_model, ids, fields=None, load=None, check_fields=True):
        if check_fields:
            ds_fields = ds_model.fields_get_keys()
            fields = [f for f in fields if f in ds_fields]
        kwargs = {
            key: val
            for key, val in [('fields', fields),
                             ('load', load),
                             ('context', self._get_context())]
            if val is not None}
        return ds_model.read(ids, **kwargs)

    @api.model
    def of_datastore_read_group(
            self, ds_model, domain, fields, groupby, offset=None, limit=None, orderby=None, lazy=None):
        kwargs = {
            key: val
            for key, val in [('offset', offset),
                             ('limit', limit),
                             ('orderby', orderby),
                             ('lazy', lazy),
                             ('context', self._get_context())]
            if val is not None}
        return ds_model.read_group(domain, fields, groupby, **kwargs)

    @api.model
    def of_datastore_search_read(self, ds_model, domain=None, fields=None, offset=0, limit=None, order=None):
        # La fonction search_read de openerplib ne fonctionne pas bien et fonctionne par un appel search() puis read().
        # On reprend le même système, mais avec nos méthodes.
        record_ids = self.of_datastore_search(ds_model, domain, offset, limit, order, count=False)
        if not record_ids:
            return []
        records = self.of_datastore_read(ds_model, record_ids, fields)
        return records
