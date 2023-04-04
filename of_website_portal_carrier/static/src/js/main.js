odoo.define('of_website_portal_carrier.main', function(require) {
"use strict";

    var ajax = require('web.ajax');
    var website = require('website.website');
    var base = require('web_editor.base');

    $('#modal_create_backorder').on('load').show();

    $('#check_all').on('click', function(event){
        var check = $(this).is(':checked');
        var $input = $('#modal_pdf').find('input:checkbox');
        if ($input.length) {
            $input.each(function() {
                $input.prop('checked', check);
            });
        }
    });
});
