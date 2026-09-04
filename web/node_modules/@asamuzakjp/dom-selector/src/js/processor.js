/**
 * processor.js
 */

/* import */
import { sortAST, unescapeSelector } from './parser.js';
import { isInvalidCombinator } from './selector.js';
import { generateException } from './utility.js';

/* constants */
import { COMBINATOR, SYNTAX_ERR } from './constant.js';

/**
 * SelectorProcessor
 * Processes raw selector branches into an internal AST format.
 */
export class SelectorProcessor {
  #context;

  /**
   * @param {import('./finder.js').Finder} context - The Finder instance.
   */
  constructor(context) {
    this.#context = context;
  }

  /**
   * Processes selector branches into the internal AST.
   * @param {Array.<object>} branches - The raw selector branches.
   * @param {string} selector - The original CSS selector string.
   * @returns {object} An object containing the ast and a descendant flag.
   */
  process(branches, selector) {
    let descendant = false;
    const ast = [];
    for (const items of branches) {
      const branch = [];
      let prevType = null;
      const itemsLen = items.length;
      if (itemsLen) {
        const leaves = new Set();
        for (let j = 0; j < itemsLen; j++) {
          const item = items[j];
          const isLast = j === itemsLen - 1;
          // Validate combinator syntax.
          if (isInvalidCombinator(item.type, prevType, isLast)) {
            const msg = `Invalid selector ${selector}`;
            this.#context.onError(
              generateException(msg, SYNTAX_ERR, this.#context.window)
            );
            return { ast: [], descendant: false, invalidate: false };
          }
          if (item.type === COMBINATOR) {
            // Flag if the branch contains descendant or child combinators.
            if (item.name === ' ' || item.name === '>') {
              descendant = true;
            }
            branch.push({ combo: item, leaves: sortAST(leaves) });
            leaves.clear();
          } else {
            // Unescape selector names and detect namespaces.
            if (item.name && typeof item.name === 'string') {
              const unescapedName = unescapeSelector(item.name);
              if (unescapedName !== item.name) {
                item.name = unescapedName;
              }
              if (/[|:]/.test(unescapedName)) {
                item.namespace = true;
              }
            }
            leaves.add(item);
          }
          prevType = item.type;
          // Handle the trailing items after the loop finishes.
          if (isLast) {
            branch.push({ combo: null, leaves: sortAST(leaves) });
            leaves.clear();
          }
        }
      }
      // Initialize the structure required for node collection.
      ast.push({ branch, dir: null, filtered: false, find: false });
    }
    return { ast, descendant };
  }
}
