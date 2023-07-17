odoo.define('of_website_portal_supplier.main', function(require) {
"use strict";

    var ajax = require('web.ajax');
    var website = require('website.website');
    var base = require('web_editor.base');

    $('#modal_divide_picking').on('load').show();

    $('#check_all').on('click', function(event){
        var check = $(this).is(':checked');
        var $input = $('#modal_pdf').find('input:checkbox');
        if ($input.length) {
            $input.each(function() {
                $input.prop('checked', check);
            });
        }
    });

    $(document).ready(function() {
        console.log('ready');
        var $input = $('.shipment_datepicker');
        console.log($input);
        if ($input.length) {
            $input.each(function() {
                $input.prop('min', new Date().toISOString().split("T")[0]);
            });
        }
    });;

});
