# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "OF Account Invoice Report Payment Extended Info",
    "summary": "Show payment extended info in invoice",
    "version": "16.0.1.0.0",
    "category": "OpenFire",
    "website": "https://www.openfire.fr",
    "author": "OpenFire",
    "license": "AGPL-3",
    "installable": True,
    "depends": ["of_account"],
    "data": [
        "data/payment_info_data.xml",
        "views/report_invoice.xml",
        "views/account_payment_method_line.xml",
    ],
}
