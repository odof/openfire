# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, models


class DMSDirectory(models.Model):
    _inherit = "dms.directory"

    @api.model
    def get_tree_data(self, domain, limit, offset):
        tree = []
        directories = self.search(domain)
        # on filtre d'abord les dossiers les plus hauts (dossiers racines)
        directories_root = directories.filtered(lambda r: r.is_root_directory)
        for directory in directories_root:
            value = {
                "id": directory.id,
                "name": directory._get_translated_name(),
                "childs": self.get_childs(directory, directories),
                "parent_id": False,
                "model": directory.res_model,
                "model_id": directory.res_id,
                "root": True,
            }
            tree.append(value)
        return tree

    def get_childs(self, directory, directories):
        tree = []
        # on retourne les enfants de directory qui sont dans directories
        res = directories.filtered(lambda r: r.parent_id.id == directory.id)
        for d in res:
            value = {
                "id": d.id,
                "name": d._get_translated_name(),
                "childs": self.get_childs(d, directories),
                "parent_id": directory.id,
                "is_virtual": False,
                "model": d.res_model,
                "model_id": d.res_id,
                "root": False,
                "count_total_files": d.count_total_files,
            }
            tree.append(value)
        return tree

    @api.model
    def get_parent_directory(self, directory_id):
        # on va chercher dossier parent
        parent_directory = self.env["dms.directory"].browse(directory_id).parent_id
        if parent_directory:
            return {
                "id": parent_directory.id,
                "name": _("Parent Folder"),
                "is_directory": True,
                "parent_id": parent_directory.id,
                "is_virtual": False,
            }
        return {}

    @api.model
    def get_directories(self, directory_id):
        # on va chercher la liste des sous dossier de ce directory_id et ses fichiers
        res = []
        directory_obj = self.env["dms.directory"]
        directories = directory_obj.search([("parent_id", "=", directory_id)])
        for directory in directories:
            res.append(
                {
                    "id": directory.id,
                    "name": directory._get_translated_name(),
                    "is_directory": True,
                    "parent_id": directory_id,
                    "is_virtual": False,
                    "count_total_files": directory.count_total_files,
                    "files": directory_obj.get_files(directory.id),
                }
            )
        return res

    @api.model
    def get_files(self, directory_id):
        # on va chercher la liste des fichiers
        res = []
        files = self.env["dms.file"].search([("directory_id", "child_of", directory_id)])
        for file in files:
            value = {
                "id": file.id,
                "name": file.name,
                "is_directory": False,
                "parent_id": file.directory_id.id,
                "is_virtual": file.of_type == "virtual",
                "content_url": file.of_content_url,
                "attachment_id": file.attachment_id.id,
                "extension": file.extension,
            }

            if file.of_content_url and file.of_type == "virtual":
                # on est sur un fichier virtuel, donc on doit lancer la génération du rapport pdf
                # ici, il y a juste à changer l'url /report/html en /report/pdf
                value["download_url"] = file.of_content_url.replace("/report/html", "/report/pdf")
            elif file.of_type == "real":
                value["download_url"] = f"/web/content/{file.attachment_id.id}/{file.name}"

            res.append(value)
        return res

    @api.model
    def get_direct_files(self, directory_id):
        # on va chercher la liste des fichiers
        res = []
        files = self.env["dms.file"].search([("directory_id", "=", directory_id)])
        for file in files:
            value = {
                "id": file.id,
                "name": file.name,
                "is_directory": False,
                "parent_id": file.directory_id.id,
                "is_virtual": file.of_type == "virtual",
                "content_url": file.of_content_url,
                "attachment_id": file.attachment_id.id,
                "extension": file.extension,
            }

            if file.of_content_url and file.of_type == "virtual":
                # on est sur un fichier virtuel, donc on doit lancer la génération du rapport pdf
                # ici, il y a juste à changer l'url /report/html en /report/pdf
                value["download_url"] = file.of_content_url.replace("/report/html", "/report/pdf")
            elif file.of_type == "real":
                value["download_url"] = f"/web/content/{file.attachment_id.id}/{file.name}"

            res.append(value)
        return res

    @api.model
    def filter_directory(self, directory_id, file_ids):
        directory_obj = self.env["dms.directory"]
        file_obj = self.env["dms.file"]

        directory = directory_obj.browse(directory_id)
        files = file_obj.browse(file_ids)

        file_directories = directory_obj.search([("file_ids", "in", file_ids)])
        parent_directories = directory_obj.search([("id", "parent_of", file_directories.ids)])

        if directory in parent_directories:
            return True
        else:
            for child_dir in directory.child_directory_ids:
                self.filter_directory(child_dir.id, files.ids)
        return False
