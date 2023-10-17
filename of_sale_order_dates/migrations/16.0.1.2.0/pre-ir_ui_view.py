import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute(
        "DELETE FROM ir_ui_view WHERE name = 'of.sale.order.dates.res.config.settings.view.form.inherit.account'"
    )
    _logger.info("Removed `of.sale.order.dates.res.config.settings.view.form.inherit.account` view")
