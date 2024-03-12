# -*- coding: utf-8 -*-

from contextlib import closing
import json
import logging
import os
import psycopg2
import shutil
import subprocess
import tempfile
import time
import zipfile

import odoo
from odoo import SUPERUSER_ID
from odoo.service import db
from odoo.service.db import exp_db_exist, _create_empty_database, _drop_conn, dump_db_manifest, exp_drop
from odoo.tools.misc import exec_pg_environ, find_pg_tool

_logger = logging.getLogger(__name__)


def get_temp_db_name(db_name):
    return '%s_temp_%u' % (db_name, + time.time())


def _sanitize_database(cr):
    """
    Cette fonction nettoie la base de donnée des données sensibles qui y sont présentes.
    La base de données doit avoir le module of_base installé pour que la fonctionnalité soit applicable.
    De plus, cette fonction installe le module web_environment_ribbon sur la base.
    """
    cr.autocommit(True)
    rows = []
    try:
        cr.execute("SELECT query, query_if FROM of_sanitize_query")
        rows = cr.fetchall()
    except psycopg2.Error, e:
        _logger.info('Sanitize DB: %s failed\n%s', cr.dbname, e)
    if rows:
        for query, query_if in rows:
            if query_if:
                cr.execute(query_if)
                if not cr.fetchall():
                    continue
            cr.execute(query)
        _logger.info('Sanitized DB: %s', cr.dbname)
    cr.autocommit(False)
    _logger.info('Installing module web_environment_ribbon on DB: %s', cr.dbname)
    cr.execute("SELECT state FROM ir_module_module WHERE name = 'web_environment_ribbon'")
    if cr.fetchall()[0][0] in ('uninstalled', 'to install'):
        env = odoo.api.Environment(cr, SUPERUSER_ID, {})
        module_ribbon = env['ir.module.module'].search([('name', '=', 'web_environment_ribbon')])
        if module_ribbon.state in ('uninstalled', 'to install'):
            module_ribbon.state = 'to install'
            env['base.module.upgrade'].upgrade_module()
    _logger.info('Module web_environment_ribbon installed on DB: %s', cr.dbname)


def sanitize_database(db_name):
    try:
        registry = odoo.modules.registry.Registry(db_name)
        with registry.cursor() as cr:
            _sanitize_database(cr)
    except:
        # En cas d'échec du nettoyage de la base, on la supprime
        # Code copié de la fonction odoo.service.db.exp_drop
        db = odoo.sql_db.db_connect('postgres')
        with closing(db.cursor()) as cr:
            cr.autocommit(True)  # avoid transaction block
            _drop_conn(cr, db_name)
            try:
                cr.execute('DROP DATABASE "%s"' % db_name)
            except Exception, e:
                _logger.info('DROP DB: %s failed:\n%s', db_name, e)
            else:
                _logger.info('DROP DB: %s', db_name)
        raise


def get_minimum_files_query():
    return (
        "SELECT store_fname FROM ir_attachment "
        "WHERE"
        # Fichiers css/less ou javascript
        "   mimetype IN ('text/css', 'application/javascript') "
        # Icônes des menus
        "   OR (res_model = 'ir.ui.menu' AND res_field = 'web_icon_data') "
        # Fichiers des modèles de courrier
        "   OR (res_model = 'of.mail.template' AND res_field = 'file')")


native_dump_db = db.dump_db


def dump_db(db_name, stream, backup_format='zip', **kwargs):
    # Utilisation de kwargs en raison d'autres héritages possibles ajoutant des champs
    # (e.g. module smile_anonymization)
    if backup_format != 'minizip':
        return native_dump_db(db_name, stream, backup_format=backup_format, **kwargs)
    with odoo.tools.osutil.tempdir() as dump_dir:
        filestore = odoo.tools.config.filestore(db_name)
        db = odoo.sql_db.db_connect(db_name)
        if os.path.exists(filestore):
            # On ne conserve que le minimum de fichiers
            dump_filestore_dir = os.path.join(dump_dir, 'filestore')
            with db.cursor() as cr:
                cr.execute(get_minimum_files_query())
                for store_fname, in cr.fetchall():
                    file_path = os.path.join(filestore, store_fname)
                    if not os.path.exists(file_path):
                        continue
                    # Création du répertoire
                    fdir = os.path.join(dump_filestore_dir, store_fname.rpartition('/')[0])
                    if not os.path.exists(fdir):
                        os.makedirs(fdir)
                    # Copie du fichier
                    shutil.copy(
                        file_path,
                        os.path.join(dump_filestore_dir, store_fname))
        with open(os.path.join(dump_dir, 'manifest.json'), 'w') as fh:
            with db.cursor() as cr:
                json.dump(dump_db_manifest(cr), fh, indent=4)
        odoo.tools.exec_pg_command(
            'pg_dump', '--no-owner',
            '--file=' + os.path.join(dump_dir, 'dump.sql'),
            db_name)
        if stream:
            odoo.tools.osutil.zip_dir(
                dump_dir, stream, include_dir=False, fnct_sort=lambda file_name: file_name != 'dump.sql')
        else:
            t = tempfile.TemporaryFile()
            odoo.tools.osutil.zip_dir(
                dump_dir, t, include_dir=False, fnct_sort=lambda file_name: file_name != 'dump.sql')
            t.seek(0)
            return t


db.dump_db = dump_db


def exp_duplicate_database(db_original_name, db_name, sanitize=True, drop_existing=False):
    """
    Surcharge OpenFire:
    - ajoute des paramètres sanitize et drop_existing
    - utilise un nom de base temporaire pour éviter que la base soit chargée par un processus Odoo avant la fin
    - utilise les fonctions dump/restore à la place de la duplication postgres, qui nécessitait une coupure des
      transactions en cours
    """
    _logger.info('Duplicate database `%s` to `%s`.', db_original_name, db_name)

    existing = exp_db_exist(db_name)
    if existing and not drop_existing:
        _logger.info('DUPLICATE DB: %s already exists', db_name)
        raise Exception("Database %s already exists !" % db_name)
    temp_db_name = get_temp_db_name(db_name)
    _create_empty_database(temp_db_name)

    # Copie des données
    pg_env = exec_pg_environ()
    dump_process = subprocess.Popen(
        (find_pg_tool('pg_dump'), '--no-owner', db_original_name),
        bufsize=-1,
        stdout=subprocess.PIPE,
        close_fds=True,
        env=pg_env
    )
    restore_process = subprocess.Popen(
        (find_pg_tool('psql'), '--dbname=' + temp_db_name),
        stdin=dump_process.stdout,
        stdout=subprocess.PIPE,
        env=pg_env
    )
    _, error = restore_process.communicate()
    if error:
        exp_drop(temp_db_name)
        raise Exception(u"Erreur lors de la duplication de la base\n%s" % (error,))

    registry = odoo.modules.registry.Registry.new(temp_db_name)
    with registry.cursor() as cr:
        # if it's a copy of a database, force generation of a new dbuuid
        env = odoo.api.Environment(cr, SUPERUSER_ID, {})
        env['ir.config_parameter'].init(force=True)

    # Déplacement du filestore
    from_fs = odoo.tools.config.filestore(db_original_name)
    to_fs = odoo.tools.config.filestore(db_name)
    if os.path.exists(from_fs) and not os.path.exists(to_fs):
        if sanitize:
            # On utilise la même réduction de pièces jointes qu'avec les dumps 'minizip'
            temp_db = odoo.sql_db.db_connect(temp_db_name)
            with temp_db.cursor() as cr:
                cr.execute(get_minimum_files_query())
                for store_fname, in cr.fetchall():
                    file_path = os.path.join(from_fs, store_fname)
                    if not os.path.exists(file_path):
                        continue
                    # Création du répertoire
                    fdir = os.path.join(to_fs, store_fname.rpartition('/')[0])
                    if not os.path.exists(fdir):
                        os.makedirs(fdir)
                    # Copie du fichier
                    shutil.copy(
                        file_path,
                        os.path.join(to_fs, store_fname))
        else:
            shutil.copytree(from_fs, to_fs)

    if sanitize:
        sanitize_database(temp_db_name)
    if existing:
        _logger.info('DUPLICATE DB: Dropping database %s', db_name)
        exp_drop(db_name)
    db = odoo.sql_db.db_connect('postgres')
    with closing(db.cursor()) as cr:
        cr.autocommit(True)     # avoid transaction block
        _drop_conn(cr, temp_db_name)
        cr.execute("""ALTER DATABASE "%s" RENAME TO "%s" """ % (temp_db_name, db_name))
    return True


db.exp_duplicate_database = exp_duplicate_database


def exp_restore(db_name, data, copy=False, sanitize=True, drop_existing=False):
    # Surcharge OpenFire qui ajoute les paramètres sanitize et drop_existing
    def chunks(d, n=8192):
        for i in range(0, len(d), n):
            yield d[i:i+n]
    data_file = tempfile.NamedTemporaryFile(delete=False)
    try:
        for chunk in chunks(data):
            data_file.write(chunk.decode('base64'))
        data_file.close()
        restore_db(db_name, data_file.name, copy=copy, sanitize=sanitize, drop_existing=drop_existing)
    finally:
        os.unlink(data_file.name)
    return True


db.exp_restore = exp_restore


def restore_db(db, dump_file, copy=False, sanitize=True, drop_existing=False):
    """
    Surcharge OpenFire:
    - ajoute les paramètres sanitize et drop_existing
    - utilise un nom de base temporaire pour éviter que la base soit chargée par un processus Odoo avant la fin
    - une base partiellement restaurée est supprimée
    """
    assert isinstance(db, basestring)

    existing = exp_db_exist(db)
    if existing and not drop_existing:
        _logger.info('RESTORE DB: %s already exists', db)
        raise Exception("Database %s already exists !" % db)

    temp_db = get_temp_db_name(db)
    _create_empty_database(temp_db)

    filestore_path = None
    with odoo.tools.osutil.tempdir() as dump_dir:
        if zipfile.is_zipfile(dump_file):
            # v8 format
            with zipfile.ZipFile(dump_file, 'r') as z:
                # only extract known members!
                filestore = [m for m in z.namelist() if m.startswith('filestore/')]
                z.extractall(dump_dir, ['dump.sql'] + filestore)

                if filestore:
                    filestore_path = os.path.join(dump_dir, 'filestore')

            pg_cmd = 'psql'
            pg_args = ['-q', '-f', os.path.join(dump_dir, 'dump.sql')]

        else:
            # <= 7.0 format (raw pg_dump output)
            pg_cmd = 'pg_restore'
            pg_args = ['--no-owner', dump_file]

        args = []
        args.append('--dbname=' + temp_db)
        pg_args = args + pg_args

        try:
            if odoo.tools.exec_pg_command(pg_cmd, *pg_args):
                raise Exception("Couldn't restore database")
        except Exception:
            # La base a pu se créer quand-même, il vaut mieux la supprimer
            # Code copié de la fonction exp_drop de odoo/service/db.py
            db = odoo.sql_db.db_connect('postgres')
            with closing(db.cursor()) as cr:
                cr.autocommit(True)  # avoid transaction block
                _drop_conn(cr, temp_db)
                try:
                    cr.execute('DROP DATABASE "%s"' % temp_db)
                except Exception, e:
                    _logger.info('DROP DB: %s failed:\n%s', temp_db, e)
                else:
                    _logger.info('DROP DB: %s', temp_db)
            raise

        registry = odoo.modules.registry.Registry.new(temp_db)
        with registry.cursor() as cr:
            env = odoo.api.Environment(cr, SUPERUSER_ID, {})
            if copy:
                # if it's a copy of a database, force generation of a new dbuuid
                env['ir.config_parameter'].init(force=True)

            if odoo.tools.config['unaccent']:
                try:
                    with cr.savepoint():
                        cr.execute("CREATE EXTENSION unaccent")
                except psycopg2.Error:
                    pass
        if sanitize:
            sanitize_database(temp_db)
        if existing:
            _logger.info('RESTORE DB: Dropping database %s', db)
            exp_drop(db)
        postgres_db = odoo.sql_db.db_connect('postgres')
        # On renomme la base temporaire (code copié de exp_rename)
        with closing(postgres_db.cursor()) as cr:
            cr.autocommit(True)     # avoid transaction block
            _drop_conn(cr, temp_db)
            try:
                cr.execute('ALTER DATABASE "%s" RENAME TO "%s"' % (temp_db, db))
                _logger.info('RENAME DB: %s -> %s', temp_db, db)
            except Exception, e:
                _logger.info('RENAME DB: %s -> %s failed:\n%s', temp_db, db, e)
                raise Exception("Couldn't rename database %s to %s: %s" % (temp_db, db, e))
        if filestore_path:
            registry = odoo.modules.registry.Registry.new(db)
            with registry.cursor() as cr:
                env = odoo.api.Environment(cr, SUPERUSER_ID, {})
                filestore_dest = env['ir.attachment']._filestore()
                shutil.move(filestore_path, filestore_dest)

    _logger.info('RESTORE DB: %s', db)


db.restore_db = restore_db
