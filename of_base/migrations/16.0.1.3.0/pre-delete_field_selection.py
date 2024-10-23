# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)


def migrate(cr, version):
    cr.execute(
        """DELETE FROM IR_MODEL_FIELDS_SELECTION
WHERE
    FIELD_ID IN (
        SELECT
            ID
        FROM
            IR_MODEL_FIELDS
        WHERE
            MODEL = 'of.connector.config.settings'
    )"""
    )
