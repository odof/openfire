/** @odoo-module **/

import { ViewCompiler } from "@web/views/view_compiler";

export class PlanningCompiler extends ViewCompiler {}
PlanningCompiler.OWL_DIRECTIVE_WHITELIST = [
    ...ViewCompiler.OWL_DIRECTIVE_WHITELIST,
    "t-name",
    "t-esc",
    "t-out",
    "t-set",
    "t-value",
    "t-if",
    "t-else",
    "t-elif",
    "t-foreach",
    "t-as",
    "t-key",
    "t-att.*",
    "t-call",
    "t-translation",
];
