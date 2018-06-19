# -*- coding: utf-8 -*-
import logging
import threading

from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)

try:
    import openerplib  # sudo easy_install openerp-client-lib
except (ImportError, IOError) as err:
    _logger.debug(err)

#import socket # Ne pas supprimer cette ligne, voir fonction connect()

class OfDatastoreConnector(models.AbstractModel):
    u"""
    Fonctions de communication avec le serveur.
    Toute communication distante doit se faire par appel de ces fonctions.
    Le changement d'outil de connexion (erppeek, openerplib, odoorpc) peut ainsi se faire par "simple"
        redéfinition des méthodes de cette classe.
    """
    _name = 'of.datastore.connector'


    @api.multi
    def of_datastore_connect(self):
        # Connection à la base du fournisseur
        res = {}
        # Utilisation d'un thread pour stopper une connexion trop longue
        class FuncThread(threading.Thread):
            def __init__(self):
                threading.Thread.__init__(self)
                self.result = None

            def run(self):
                cli = client
                try:
                    if not cli:
                        server_address = supplier.server_address

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
                                                           login=supplier.login, password=supplier.password)
                    # Operation pour verifier la connexion
                    self.result = cli.get_model('res.users').search([]) and cli or ''
                except Exception, exc:
                    self.result = _(str(exc))

        for supplier in self:
            clients = self._datastore_clients.get(supplier.id,[])
            client = clients and clients.pop()
            while client:
                it = FuncThread()
                it.start()
                it.join(10) # attente 10 secondes ou jusqu'à la fin du thread
                if it.result:
                    # On a trouvé une connexion valide
                    break

                if it.isAlive():
                    # Depassement du délai de connexion
                    # Il n'y a pas de fonction pour forcer l'arrêt d'un thread... il se terminera tout seul

                    # La connexion est probablement toujours valide, mais victime d'un ralentissement internet
                    # Il est inutile de la supprimer, de tester les autres connexions, ou d'en créer une nouvelle
                    self.free_connection({supplier.id: client})
                    client = _(u"Délai de connexion expiré")
                    break
                client = clients and clients.pop()

            if not client:
                # Pas de client valide, on tente une connexion
                it = FuncThread()
                it.start()
                it.join(10) # attente 10 secondes ou jusqu'à la fin du thread
                if it.isAlive():
                    client = _(u"Délai de connexion expiré")
                else:
                    client = it.result
            res[supplier.id] = client
        return res

    @api.model
    def of_datastore_free_connection(self, clients):
        for supplier_id, client in clients.iteritems():
            if not isinstance(client, basestring):
                self._datastore_clients.setdefault(supplier_id, []).append(client)
        return True

    @api.model
    def of_datastore_get_model(self, ds_client, model_name):
        ds_client.ensure_one()
        return ds_client.get_model(model_name)

    @api.model
    def of_datastore_search(self, ds_model, args, offset=None, limit=None, order=None, count=None):
        kwargs = {key: val
                  for key,val in [('offset', offset),
                                  ('limit', limit),
                                  ('order', order),
                                  ('count', count)]
                  if val is not None}
        return ds_model.search(args, **kwargs)

    @api.model
    def of_datastore_name_search(self, ds_model, name=None, args=None, operator=None, limit=None):
        kwargs = {key: val
                  for key,val in [('name', name),
                                  ('args', args),
                                  ('operator', operator),
                                  ('limit', limit)]
                  if val is not None}
        return ds_model.name_search(**kwargs)

    @api.model
    def of_datastore_name_get(self, ds_model, ids):
        return ds_model.name_get(ids)

    @api.model
    def of_datastore_read(self, ds_model, ids, fields=None, load=None):
        kwargs = {key: val
                  for key,val in [('fields', fields),
                                  ('load', load)]
                  if val is not None}
        return ds_model.read(ids, **kwargs)

    @api.model
    def of_datastore_read_group(self, ds_model, domain, fields, groupby, offset=None, limit=None, orderby=None, lazy=None, context=None):
        kwargs = {key: val
                  for key,val in [('offset', offset),
                                  ('limit', limit),
                                  ('orderby', orderby),
                                  ('lazy', lazy),
                                 ('context', context)]
                  if val is not None}
        return ds_model.read_group(domain, fields, groupby, **kwargs)
