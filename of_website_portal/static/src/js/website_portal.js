odoo.define('of_website_portal.website_portal', function (require) {
    'use strict';

    var base = require('web_editor.base');

    $(window).on('beforeunload', function () {
        return "Êtes-vous sûr de vouloir quitter cette page ?Si vous quittez la page  Les informations non enregistrées seront perdues.";
    });

});
