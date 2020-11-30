odoo.define('of_website_fuel_choice.fuel_choice', function (require) {
    "use strict";

    var base = require('web_editor.base');
    var ajax = require('web.ajax');

    if(!$('.oe_website_fuel').length) {
        return $.Deferred().reject("DOM doesn't contain '.oe_website_fuel'");
    }

    var clickwatch = (function(){
          var timer = 0;
          return function(callback, ms){
            clearTimeout(timer);
            timer = setTimeout(callback, ms);
          };
    })();

    $('.oe_website_fuel').each(function () {
        var oe_website_fuel = this;

        if ($(".fuel_choice_autoformat").length) {
            $(oe_website_fuel).on('change', "select[name='fuel_id']", function () {
                clickwatch(function() {
                    if ($("#fuel_id").val()) {
                        ajax.jsonRpc("/fuel_choice/fuel_infos/" + $("#fuel_id").val(), 'call', {}).then(
                            function(data) {
                                // Populate lengths and display
                                var selectLengths = $("select[name='length']");
                                if (selectLengths.data('init')===0 || selectLengths.find('option').length===1) {
                                    if (data.lengths.length > 0) {
                                        selectLengths.html('');
                                        _.each(data.lengths, function(x) {
                                            var opt = $('<option>').text(x)
                                                .attr('value', x);
                                            selectLengths.append(opt);
                                        });
                                        selectLengths.parent('div').show();
                                    }
                                    else {
                                        selectLengths.val('').parent('div').hide();
                                    }
                                    selectLengths.data('init', 0);
                                }
                                else {
                                    selectLengths.data('init', 0);
                                }

                                // Display split
                                var checkboxSplit = $("input[name='split']");
                                if (data.splits.length > 1) {
                                    checkboxSplit.parent('div').show();
                                }
                                else {
                                    checkboxSplit.attr('checked', false)
                                    checkboxSplit.parent('div').hide();
                                }
                            }
                        );
                    }
                    else
                    {
                        $("select[name='length']").val('').parent('div').hide();
                        $("input[name='split']").parent('div').hide();
                    }
                }, 500);
            });
            $(oe_website_fuel).on('change', "select[name='checkout_id']", function () {
                clickwatch(function() {
                    if ($("#checkout_id").val()) {
                        ajax.jsonRpc("/fuel_choice/checkout_infos/" + $("#checkout_id").val(), 'call', {}).then(
                            function(data) {
                                // Display address
                                var addressBlock = $("div[name='address']");
                                if (data.delivery) {
                                    addressBlock.show();
                                }
                                else {
                                    addressBlock.hide();
                                }
                            }
                        );
                    }
                    else
                    {
                        $("div[name='address']").hide();
                    }
                }, 500);
            });
        }
        $("select[name='fuel_id']").change();
        $("select[name='checkout_id']").change();
    });
});
