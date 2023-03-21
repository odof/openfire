odoo.define('of_lab.lab', function (require) {
    "use strict";

    var base = require('web_editor.base');
    var ajax = require('web.ajax');
    var utils = require('web.utils');
    var core = require('web.core');
    var config = require('web.config');
    var _t = core._t;

    if(!$('.of_lab').length) {
        return $.Deferred().reject("DOM doesn't contain '.of_lab'");
    }

    $('.of_lab').each(function () {
        var of_lab_container = this;

        // Pop-up application mobile
        $(of_lab_container).on('click', '.of_lab_1', function() {
            event.preventDefault();
            ajax.jsonRpc("/lab/mobile_app_modal", 'call', {
            }).then(function (modal) {
                var $modal = $(modal);

                // Affichage de la pop-up
                $(of_lab_container).addClass('css_options');
                $modal.appendTo($(of_lab_container))
                .modal()
                .on('hidden.bs.modal', function () {
                    $(of_lab_container).removeClass('css_options');
                    $(this).remove();
                });
            });
        });

        // Pop-up signature électronique
        $(of_lab_container).on('click', '.of_lab_2', function() {
            event.preventDefault();
            ajax.jsonRpc("/lab/yousign_modal", 'call', {
            }).then(function (modal) {
                var $modal = $(modal);

                // Affichage de la pop-up
                $(of_lab_container).addClass('css_options');
                $modal.appendTo($(of_lab_container))
                .modal()
                .on('hidden.bs.modal', function () {
                    $(of_lab_container).removeClass('css_options');
                    $(this).remove();
                });

                // Gestion du submit
                $('#lab_yousign_modal_form').on('submit', function(e) {
                    e.preventDefault();

                    // Reinit error display
                    var error_p = $modal.find("#modal_error");
                    error_p.addClass('o_hidden');
                    error_p.empty();

                    var email = $("input[name='email']").val();
                    var mobile = $("input[name='mobile']").val();

                    ajax.jsonRpc("/lab/yousign_modal/process", 'call', {
                        'email': email, 'mobile': mobile
                    }).then(function (res) {
                        if (res[1]) {
                            // Error
                            error_p.removeClass('o_hidden');
                            error_p.append(res[2]);
                        }
                        else {
                            // Close modal
                            $modal.modal('hide');
                            $(of_lab_container).removeClass('css_options');
                            $(this).remove();

                            // Open tab
                            window.open('/web#action=of_lab.of_yousign_sale_demo_action', '_blank').focus();
                        }
                    });
                });
            });
        });
    });
});
