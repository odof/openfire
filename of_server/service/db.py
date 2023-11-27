# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64
import json
import logging
import os
import shutil
import subprocess  # nosec B404
import tempfile
import time
import zipfile
from contextlib import closing

import psycopg2
from psycopg2 import sql

import odoo
import odoo.release
import odoo.sql_db
import odoo.tools
from odoo import SUPERUSER_ID
from odoo.service import db
from odoo.service.db import (
    DatabaseExists,
    _create_empty_database,
    _drop_conn,
    check_db_management_enabled,
    dump_db_manifest,
    exp_db_exist,
    exp_drop,
)
from odoo.tools import exec_pg_environ, find_pg_tool

_logger = logging.getLogger(__name__)


def get_temp_db_name(db_name):
    return f'{db_name}_temp_{int(time.time())}'


def _sanitize_database(cr):
    """
    Cette fonction nettoie la base de donnée des données sensibles qui y sont présentes.
    La base de données doit avoir le module of_base installé pour que la fonctionnalité soit applicable.
    De plus, cette fonction installe le module web_environment_ribbon sur la base.
    """
    cr._cnx.autocommit = True
    rows = []
    try:
        cr.execute("SELECT query, query_if FROM of_sanitize_query")
        rows = cr.fetchall()
    except psycopg2.Error as e:
        _logger.info('Sanitize DB: %s failed\n%s', cr.dbname, e)
    if rows:
        for query, query_if in rows:
            if query_if:
                cr.execute(query_if)
                if not cr.fetchall():
                    continue
            cr.execute(query)
        _logger.info('Sanitized DB: %s', cr.dbname)
    cr._cnx.autocommit = False
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
    except Exception:
        # En cas d'échec du nettoyage de la base, on la supprime
        # Code copié de la fonction odoo.service.db.exp_drop
        db = odoo.sql_db.db_connect('postgres')
        with closing(db.cursor()) as cr:
            # database-altering operations cannot be executed inside a transaction
            cr._cnx.autocommit = True
            _drop_conn(cr, db_name)
            try:
                cr.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(db_name)))
            except Exception as e:
                _logger.info('DROP DB: %s failed:\n%s', db_name, e)
            else:
                _logger.info('DROP DB: %s', db_name)
        raise


def get_minimum_files_query():
    return (
        "SELECT store_fname FROM ir_attachment "
        "WHERE"
        # Fichiers css/less ou javascript
        "   mimetype IN ('text/css', 'application/javascript', 'image/x-icon') "
        # Icônes des menus
        "   OR (res_model = 'ir.ui.menu' AND res_field = 'web_icon_data') "
        # Fichiers des modèles de courrier
        "   OR (res_model = 'of.custom.document' AND res_field = 'file')"
    )


native_dump_db = db.dump_db


@check_db_management_enabled
def dump_db(db_name, stream, backup_format='zip', **kwargs):
    """Dump database `db` into file-like object `stream` if stream is None
    return a file object with the dump

    Override de la fonction odoo.service.db.dump_db.
    On ajoute la possibilité de faire un dump au format 'minizip' qui ne conserve que le minimum de fichiers.

    Utilisation de kwargs en raison d'autres héritages possibles ajoutant des champs (e.g. module smile_anonymization)
    """
    if backup_format != 'minizip':
        return native_dump_db(db_name, stream, backup_format=backup_format, **kwargs)
    with tempfile.TemporaryDirectory() as dump_dir:
        filestore = odoo.tools.config.filestore(db_name)
        db = odoo.sql_db.db_connect(db_name)
        if os.path.exists(filestore):
            # On ne conserve que le minimum de fichiers
            dump_filestore_dir = os.path.join(dump_dir, 'filestore')
            with db.cursor() as cr:
                cr.execute(get_minimum_files_query())
                for (store_fname,) in cr.fetchall():
                    file_path = os.path.join(filestore, store_fname)
                    if not os.path.exists(file_path):
                        continue
                    # Création du répertoire
                    fdir = os.path.join(dump_filestore_dir, store_fname.rpartition('/')[0])
                    if not os.path.exists(fdir):
                        os.makedirs(fdir)
                    # Copie du fichier
                    shutil.copy(file_path, os.path.join(dump_filestore_dir, store_fname))
        with open(os.path.join(dump_dir, 'manifest.json'), 'w') as fh:
            with db.cursor() as cr:
                json.dump(dump_db_manifest(cr), fh, indent=4)

        subprocess.run(  # nosec B603
            [find_pg_tool('pg_dump'), f"--file={os.path.join(dump_dir, 'dump.sql')}", '--no-owner', db_name],
            env=exec_pg_environ(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )

        if stream:
            odoo.tools.osutil.zip_dir(
                dump_dir, stream, include_dir=False, fnct_sort=lambda file_name: file_name != 'dump.sql'
            )
        else:
            t = tempfile.TemporaryFile()
            odoo.tools.osutil.zip_dir(
                dump_dir, t, include_dir=False, fnct_sort=lambda file_name: file_name != 'dump.sql'
            )
            t.seek(0)
            return t


# override odoo.service.db.dump_db
db.dump_db = dump_db


@check_db_management_enabled
def exp_duplicate_database(db_original_name, db_name, neutralize_database=False, sanitize=True, drop_existing=False):
    """Surcharge OpenFire :

    - ajout d'un paramètre `sanitize` qui permet de nettoyer la base de données des données sensibles
    - ajout d'un paramètre `drop_existing` qui permet de supprimer une base de données existante
    - utilisation d'un nom de base temporaire pour éviter que la base soit chargée par un processus Odoo avant la fin
        de la duplication.
    """
    _logger.info('Duplicate database `%s` to `%s`.', db_original_name, db_name)

    existing = exp_db_exist(db_name)
    if existing and not drop_existing:
        _logger.info('DUPLICATE DB: %s already exists', db_name)
        raise DatabaseExists(f"Database {db_name} already exists !")

    temp_db_name = get_temp_db_name(db_name)
    odoo.sql_db.close_db(db_original_name)
    db = odoo.sql_db.db_connect('postgres')
    with closing(db.cursor()) as cr:
        # database-altering operations cannot be executed inside a transaction
        cr._cnx.autocommit = True
        _drop_conn(cr, db_original_name)
        cr.execute(
            sql.SQL("CREATE DATABASE {} ENCODING 'unicode' TEMPLATE {}").format(
                sql.Identifier(temp_db_name), sql.Identifier(db_original_name)
            )
        )

    registry = odoo.modules.registry.Registry.new(temp_db_name)
    with registry.cursor() as cr:
        # if it's a copy of a database, force generation of a new dbuuid
        env = odoo.api.Environment(cr, SUPERUSER_ID, {})
        env['ir.config_parameter'].init(force=True)
        if neutralize_database:
            odoo.modules.neutralize.neutralize_database(cr)

    from_fs = odoo.tools.config.filestore(db_original_name)
    to_fs = odoo.tools.config.filestore(db_name)
    if os.path.exists(from_fs) and not os.path.exists(to_fs):
        if sanitize:
            # On utilise la même réduction de pièces jointes qu'avec les dumps 'minizip'
            temp_db = odoo.sql_db.db_connect(temp_db_name)
            with temp_db.cursor() as cr:
                cr.execute(get_minimum_files_query())
                for (store_fname,) in cr.fetchall():
                    file_path = os.path.join(from_fs, store_fname)
                    if not os.path.exists(file_path):
                        continue
                    # Création du répertoire
                    fdir = os.path.join(to_fs, store_fname.rpartition('/')[0])
                    if not os.path.exists(fdir):
                        os.makedirs(fdir)
                    # Copie du fichier
                    shutil.copy(file_path, os.path.join(to_fs, store_fname))
        else:
            shutil.copytree(from_fs, to_fs)
    if sanitize:
        sanitize_database(temp_db_name)
    if existing:
        _logger.info('DUPLICATE DB: Dropping database %s', db_name)
        exp_drop(db_name)
    with closing(db.cursor()) as cr:
        # database-altering operations cannot be executed inside a transaction
        cr._cnx.autocommit = True
        _drop_conn(cr, temp_db_name)
        cr.execute(
            sql.SQL('ALTER DATABASE {} RENAME TO {}').format(sql.Identifier(temp_db_name), sql.Identifier(db_name))
        )

    # remove temporary database registry to avoid cron jobs to run on it
    odoo.modules.registry.Registry.delete(temp_db_name)

    return True


# override odoo.service.db.exp_duplicate_database
db.exp_duplicate_database = exp_duplicate_database


@check_db_management_enabled
def exp_restore(db_name, data, copy=False, sanitize=True, drop_existing=False):
    """Surcharge OpenFire :
    - ajout d'un paramètre `sanitize` qui permet de nettoyer la base de données des données sensibles
    - ajout d'un paramètre `drop_existing` qui permet de supprimer une base de données existante
    """

    def chunks(d, n=8192):
        for i in range(0, len(d), n):
            yield d[i : i + n]

    data_file = tempfile.NamedTemporaryFile(delete=False)
    try:
        for chunk in chunks(data):
            data_file.write(base64.b64decode(chunk))
        data_file.close()
        restore_db(db_name, data_file.name, copy=copy, sanitize=sanitize, drop_existing=drop_existing)
    finally:
        os.unlink(data_file.name)
    return True


# override odoo.service.db.exp_restore
db.exp_restore = exp_restore


@check_db_management_enabled
def restore_db(db, dump_file, copy=False, neutralize_database=False, sanitize=True, drop_existing=False):
    """Surcharge OpenFire:
    - ajout d'un paramètre `sanitize` qui permet de nettoyer la base de données des données sensibles
    - ajout d'un paramètre `drop_existing` qui permet de supprimer une base de données existante
    - utilisation d'un nom de base temporaire pour éviter que la base soit chargée par un processus Odoo avant la fin
        de la restauration.
    - une base partiellement restaurée est supprimée
    """

    assert isinstance(db, str)
    existing = exp_db_exist(db)
    if existing and not drop_existing:
        _logger.warning('RESTORE DB: %s already exists', db)
        raise DatabaseExists("Database already exists")

    _logger.info('RESTORING DB: %s', db)
    temp_db_name = get_temp_db_name(db)
    _create_empty_database(temp_db_name)

    filestore_path = None
    with tempfile.TemporaryDirectory() as dump_dir:
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

        try:
            r = subprocess.run(  # nosec B603
                [find_pg_tool(pg_cmd), f'--dbname={temp_db_name}', *pg_args],
                env=exec_pg_environ(),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.STDOUT,
            )
            if r.returncode != 0:
                raise Exception("Couldn't restore database")
        except Exception:
            # La base a pu se créer quand-même, il vaut mieux la supprimer
            # Code copié de la fonction exp_drop de odoo/service/db.py
            db = odoo.sql_db.db_connect('postgres')
            with closing(db.cursor()) as cr:
                # database-altering operations cannot be executed inside a transaction
                cr._cnx.autocommit = True
                _drop_conn(cr, temp_db_name)

                try:
                    cr.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(temp_db_name)))
                except Exception as e:
                    _logger.info('DROP DB: %s failed:\n%s', temp_db_name, e)
                    raise Exception(f"Couldn't drop database {temp_db_name}: {e}") from e
                else:
                    _logger.info('DROP DB: %s', temp_db_name)
            raise

        registry = odoo.modules.registry.Registry.new(temp_db_name)
        with registry.cursor() as cr:
            env = odoo.api.Environment(cr, SUPERUSER_ID, {})
            if copy:
                # if it's a copy of a database, force generation of a new dbuuid
                env['ir.config_parameter'].init(force=True)
            if neutralize_database:
                odoo.modules.neutralize.neutralize_database(cr)

        if sanitize:
            sanitize_database(temp_db_name)
        if existing:
            _logger.info('RESTORE DB: Dropping database %s', db)
            exp_drop(db)

        postgres_db = odoo.sql_db.db_connect('postgres')
        with closing(postgres_db.cursor()) as cr:
            # database-altering operations cannot be executed inside a transaction
            cr._cnx.autocommit = True
            _drop_conn(cr, temp_db_name)
            try:
                cr.execute(
                    sql.SQL('ALTER DATABASE {} RENAME TO {}').format(sql.Identifier(temp_db_name), sql.Identifier(db))
                )
                _logger.info('RENAME DB: %s -> %s', temp_db_name, db)
            except Exception as e:
                _logger.info('RENAME DB: %s -> %s failed:\n%s', temp_db_name, db, e)
                raise Exception(f"Couldn't rename database {temp_db_name} to {db}: {e}") from e

        if filestore_path:
            registry = odoo.modules.registry.Registry.new(db)
            with registry.cursor() as cr:
                env = odoo.api.Environment(cr, SUPERUSER_ID, {})
                filestore_dest = env['ir.attachment']._filestore()
                shutil.move(filestore_path, filestore_dest)

    # remove temporary database registry to avoid cron jobs try to run on it
    odoo.modules.registry.Registry.delete(temp_db_name)

    _logger.info('RESTORE DB: %s', db)


# override odoo.service.db.restore_db
db.restore_db = restore_db
