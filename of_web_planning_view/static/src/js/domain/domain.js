/** @odoo-module **/

import { Domain } from "@web/core/domain";


/**
 * Return a new domain with `neutralized` leaves (for the leaves that are applied on the field that are part of
 * keysToRemove).
 * @param {DomainRepr} domain
 * @param {string[]} keysToRemove
 * @return {Domain}
 */
export function removeDomainLeaves(domain, keysToRemove) {
    function processLeaf(elements, idx, operatorCtx, newDomain) {
        const leaf = elements[idx];
        if (leaf.type === 10) {
            if (keysToRemove.includes(leaf.value[0].value)) {
                if (operatorCtx === "&") {
                    newDomain.ast.value.push(...Domain.TRUE.ast.value);
                } else if (operatorCtx === "|") {
                    newDomain.ast.value.push(...Domain.FALSE.ast.value);
                }
            } else {
                newDomain.ast.value.push(leaf);
            }
            return 1;
        } else if (leaf.type === 1) {
            // Special case to avoid OR ('|') that can never resolve to true
            if (
                leaf.value === "|" &&
                elements[idx + 1].type === 10 &&
                elements[idx + 2].type === 10 &&
                keysToRemove.includes(elements[idx + 1].value[0].value) &&
                keysToRemove.includes(elements[idx + 2].value[0].value)
            ) {
                newDomain.ast.value.push(...Domain.TRUE.ast.value);
                return 3;
            }
            newDomain.ast.value.push(leaf);
            if (leaf.value === "!") {
                return 1 + processLeaf(elements, idx + 1, "&", newDomain);
            }
            const firstLeafSkip = processLeaf(elements, idx + 1, leaf.value, newDomain);
            const secondLeafSkip = processLeaf(
                elements,
                idx + 1 + firstLeafSkip,
                leaf.value,
                newDomain
            );
            return 1 + firstLeafSkip + secondLeafSkip;
        }
        return 0;
    }

    domain = new Domain(domain);
    if (domain.ast.value.length === 0) {
        return domain;
    }
    const newDomain = new Domain([]);
    processLeaf(domain.ast.value, 0, "&", newDomain);
    return newDomain;
}
