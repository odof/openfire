odoo.define('of_calculation_heat_loss.calculation_website', function (require) {
    "use strict";

    var base = require('web_editor.base');
    var ajax = require('web.ajax');
    var utils = require('web.utils');
    var core = require('web.core');
    var config = require('web.config');
    var _t = core._t;
    var Model = require('web.Model');

    $('#iframe_section').each(function () {
        // Filtre des altitudes disponibles par département
        $('input#partner_zip').on('change', function (event) {
            // Lorsque le code postal est renseigné, on récupère la liste des altitudes possibles
            var zip = this.value;
            var altitude_selector = $('select#altitude_id');

            if (zip != null && zip != undefined) {
                ajax.jsonRpc('/get_heat_loss_altitude_ids_from_zip', 'call', {'zip': zip}).then(function (altitude_ids) {
                    let j = 0;
                    let selector_options = altitude_selector.children()
                    for (let i = 1; i < selector_options.length; i++) {
                        let option = selector_options[i];
                        if (j < altitude_ids.length && option.value == altitude_ids[j]) {
                            option.style.display = 'block';
                            j++;
                        }
                        else {
                            option.style.display = 'none';
                            if (option.selected) {
                                selector_options[0].selected = true;
                            }
                        }
                    }
                });
            };
        });

        $('select#fuel_coef_id').on('change', function (event) {
            var coef_input = $('input#coef_wood');
            var fuel_coef_id = parseInt(this[this.selectedIndex].value);
            if (fuel_coef_id == NaN) {
                coef_input.val("1");
            } else {
                var fuel_coef_model = new Model('of.calculation.fuel.coef');
                if (fuel_coef_id != null && fuel_coef_id != undefined && !Number.isNaN(fuel_coef_id) && coef_input != undefined && coef_input != null) {
                    ajax.jsonRpc('/get_heat_loss_fuel_coef', 'call', {'coef_id': fuel_coef_id}).then(function (coef) {
                        if (coef != false) {
                            coef_input.val(coef.toString());
                        } else {
                            coef_input.val('1');
                        };
                    });
                };
            };
        });
    });

    try {
        // Chargement du graphe des coûts par énergie
        var fuel_consumption_values = JSON.parse($("#fuel_consumption_values").text());
        new Chart("chart_energy_consuption", {
            type: "bar",
            data: {
                labels: fuel_consumption_values.names,
                datasets: [{
                    label: "Coût annuel (€)",
                    backgroundColor: fuel_consumption_values.colors,
                    data: fuel_consumption_values.costs,
                }]
            },
            options: {
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                let label = "Coût annuel : ";
                                if (context.parsed.y !== null) {
                                    label += new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR' }).format(context.parsed.y);
                                }
                                return label;
                            }
                        }
                    }
                }
            }
        });
    } catch {}


});
