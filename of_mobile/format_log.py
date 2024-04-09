# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).


def format_log(context, log):
    """Formatte le log en ajoutant des informations contextuelles tel
    que la version de l'app client"""
    client_version = context.get("client_version")
    correlation_id = context.get("correlation_id")
    return f"[client_version:{client_version} correlation:{correlation_id}] - {log}"
