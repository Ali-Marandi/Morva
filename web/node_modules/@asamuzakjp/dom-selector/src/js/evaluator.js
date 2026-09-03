/**
 * evaluator.js
 */

/* import */
import { EventHandler } from './event.js';
import {
  matchAttributeSelector,
  matchCheckedPseudoClass,
  matchDirectionPseudoClass,
  matchLanguagePseudoClass,
  matchLinkPseudoClass,
  matchOpenPseudoClass,
  matchPlaceholderShownPseudoClass,
  matchPseudoElementSelector,
  matchRangePseudoClass,
  matchReadOnlyPseudoClass,
  matchRequiredPseudoClass,
  matchTypeSelector
} from './matcher.js';
import {
  generateCSS,
  parseSelector,
  unescapeSelector,
  walkAST
} from './parser.js';
import {
  findBestSeed,
  generateException,
  isCustomElement,
  isFocusVisible,
  isFocusableArea,
  populateHasAllowlist,
  resolveContent,
  traverseNode
} from './utility.js';

/* constants */
import {
  ATTR_SELECTOR,
  CLASS_SELECTOR,
  COMBINATOR,
  DIR_NEXT,
  DIR_PREV,
  DOCUMENT_FRAGMENT_NODE,
  ELEMENT_NODE,
  FORM_PARTS,
  HEX,
  ID_SELECTOR,
  INPUT_CHECK,
  INPUT_DATE,
  INPUT_EDIT,
  INPUT_TEXT,
  KEYS_LOGICAL,
  NEST_SELECTOR,
  NOT_SUPPORTED_ERR,
  PS_CLASS_SELECTOR,
  PS_ELEMENT_SELECTOR,
  SHOW_ALL,
  SHOW_CONTAINER,
  SYNTAX_ERR,
  TEXT_NODE,
  TYPE_SELECTOR
} from './constant.js';
const KEYS_FORM = new Set([...FORM_PARTS, 'fieldset', 'form']);
const KEYS_FORM_PS_VALID = new Set(FORM_PARTS);
const KEYS_INPUT_CHECK = new Set(INPUT_CHECK);
const KEYS_INPUT_PLACEHOLDER = new Set([...INPUT_TEXT, 'number']);
const KEYS_INPUT_RANGE = new Set([...INPUT_DATE, 'number', 'range']);
const KEYS_INPUT_REQUIRED = new Set([...INPUT_CHECK, ...INPUT_EDIT, 'file']);
const KEYS_INPUT_RESET = new Set(['button', 'reset']);
const KEYS_INPUT_SUBMIT = new Set(['image', 'submit']);
const KEYS_FORM_PS_DISABLED = new Set([
  ...FORM_PARTS,
  'fieldset',
  'optgroup',
  'option'
]);
const KEYS_PS_UNCACHE = new Set([
  'any-link',
  'defined',
  'dir',
  'link',
  'scope'
]);
const KEYS_PS_NTH_OF_TYPE = new Set([
  'first-of-type',
  'last-of-type',
  'only-of-type'
]);

/**
 * Evaluator
 * Determines if DOM elements match provided CSS selectors.
 */
export class Evaluator {
  /* private fields */
  #anbCache;
  #astCache = new WeakMap();
  #documentURL;
  #eventHandler;
  #filterLeavesCache;
  #focusWithinCache;
  #invalidateResults;
  #lastFocusVisible;
  #nthIndexCache;
  #psDefaultCache;
  #psDirCache;
  #psDisabledCache;
  #psHasFilterCache;
  #psIndeterminateCache;
  #psLangCache;
  #psValidCache;
  #results;
  #setPool;
  #setPoolIndex;
  #verifyShadowHost;
  #walkers;

  /**
   * @param {object} window - The window object.
   */
  constructor(window) {
    this.window = window;
    this.documentCache = new WeakMap();
    this.clearResults(true);
    this.#eventHandler = new EventHandler(window);
  }

  /**
   * Sets up the evaluator.
   * @param {string} selector - The CSS selector.
   * @param {object} node - Document, DocumentFragment, or Element.
   * @param {object} [opt] - Options.
   * @param {boolean} [opt.check] - Indicates if running in internal check().
   * @param {boolean} [opt.noexcept] - If true, exceptions are not thrown.
   * @param {boolean} [opt.warn] - If true, console warnings are enabled.
   * @returns {object} The evaluator instance.
   */
  setup(selector, node, opt = {}) {
    const { check, noexcept, warn } = opt;
    this.check = !!check;
    this.noexcept = !!noexcept;
    this.warn = !!warn;
    this.matchOpts = { warn: this.warn };
    [this.document, this.root, this.shadow] = resolveContent(node);
    this.node = node;
    this.pseudoElements = [];
    this.invalidate = false;
    this.clearResults();
    this.#documentURL = null;
    this.#nthIndexCache = null;
    this.#setPool = [];
    this.#setPoolIndex = 0;
    this.#verifyShadowHost = false;
    this.#walkers = null;
    return this;
  }

  /**
   * Handles errors.
   * @param {Error} e - The error object.
   * @param {object} [opt] - Options.
   * @param {boolean} [opt.noexcept] - If true, exceptions are not thrown.
   * @throws {Error} Throws an error.
   * @returns {void}
   */
  onError = (e, opt = {}) => {
    const noexcept = opt.noexcept ?? this.noexcept;
    if (noexcept) {
      return;
    }
    const isDOMException =
      e instanceof DOMException || e instanceof this.window.DOMException;
    if (isDOMException) {
      if (e.name === NOT_SUPPORTED_ERR) {
        if (this.warn) {
          console.warn(e.message);
        }
        return;
      }
      throw new this.window.DOMException(e.message, e.name);
    }
    if (e.name in this.window) {
      throw new this.window[e.name](e.message, { cause: e });
    }
    throw e;
  };

  /**
   * Clear cached results.
   * @param {boolean} all - Clear all results.
   * @returns {void}
   */
  clearResults = (all = false) => {
    this.#anbCache = null;
    this.#focusWithinCache = null;
    this.#invalidateResults = null;
    this.#psDefaultCache = null;
    this.#psDirCache = null;
    this.#psDisabledCache = null;
    this.#psHasFilterCache = null;
    this.#psIndeterminateCache = null;
    this.#psLangCache = null;
    this.#psValidCache = null;
    if (all) {
      this.#filterLeavesCache = null;
      this.#results = new WeakMap();
    }
  };

  /**
   * Matches a selector.
   * @param {object} ast - The AST.
   * @param {object} node - The Document, DocumentFragment, or Element node.
   * @param {object} opt - Options.
   * @returns {boolean} True if matches, otherwise false.
   */
  matchSelector = (ast, node, opt) => {
    if (node.nodeType === ELEMENT_NODE) {
      return this.#matchSelectorForElement(ast, node, opt);
    }
    if (
      this.shadow &&
      node.nodeType === DOCUMENT_FRAGMENT_NODE &&
      ast.type === PS_CLASS_SELECTOR
    ) {
      return this.#matchSelectorForShadowRoot(ast, node, opt);
    }
    return false;
  };

  /**
   * Matches leaves against a node with cache check.
   * @param {Array.<object>} leaves - The AST leaves to match.
   * @param {object} node - The DOM node.
   * @param {object} opt - The match options.
   * @returns {boolean} True if matched, otherwise false.
   */
  matchLeaves = (leaves, node, opt) => {
    if (!this.#invalidateResults) {
      this.#invalidateResults = new WeakMap();
    }
    const results = this.invalidate ? this.#invalidateResults : this.#results;
    let result = results.get(leaves);
    if (result) {
      const nodeResult = result.get(node);
      if (nodeResult !== undefined) {
        return nodeResult;
      }
    }
    let cacheable = true;
    if (node.nodeType === ELEMENT_NODE && KEYS_FORM.has(node.localName)) {
      cacheable = false;
    }
    let bool;
    const l = leaves.length;
    for (let i = 0; i < l; i++) {
      const leaf = leaves[i];
      switch (leaf.type) {
        case ATTR_SELECTOR:
        case ID_SELECTOR: {
          cacheable = false;
          break;
        }
        case PS_CLASS_SELECTOR: {
          if (KEYS_PS_UNCACHE.has(leaf.name)) {
            cacheable = false;
          }
          break;
        }
        default: {
          // No action needed for other types.
        }
      }
      bool = this.matchSelector(leaf, node, opt);
      if (!bool) {
        break;
      }
    }
    if (cacheable) {
      if (!result) {
        result = new WeakMap();
      }
      result.set(node, bool);
      results.set(leaves, result);
    }
    return bool;
  };

  /**
   * Returns a cached slice of the leaves array (excluding the first item).
   * @param {Array.<object>} leaves - The original AST leaves array.
   * @returns {Array.<object>} The filtered leaves.
   */
  getFilterLeaves = leaves => {
    if (!this.#filterLeavesCache) {
      this.#filterLeavesCache = new WeakMap();
    }
    let filterLeaves = this.#filterLeavesCache.get(leaves);
    if (filterLeaves) {
      return filterLeaves;
    }
    filterLeaves = leaves.slice(1);
    this.#filterLeavesCache.set(leaves, filterLeaves);
    return filterLeaves;
  };

  /**
   * Evaluates shadow host pseudo-classes.
   * @param {object} ast - The AST.
   * @param {object} node - The DocumentFragment node.
   * @returns {boolean} True if matches, otherwise false.
   */
  evaluateShadowHost = (ast, node) => {
    const { children: astChildren, name: astName } = ast;
    // Handle simple pseudo-class (no arguments).
    if (!Array.isArray(astChildren)) {
      if (astName === 'host') {
        return true;
      }
      const msg = `Invalid selector :${astName}`;
      this.onError(generateException(msg, SYNTAX_ERR, this.window));
      return false;
    }
    // Handle functional pseudo-class like :host(...).
    if (astName !== 'host' && astName !== 'host-context') {
      const msg = `Invalid selector :${astName}()`;
      this.onError(generateException(msg, SYNTAX_ERR, this.window));
      return false;
    }
    if (astChildren.length !== 1) {
      const css = generateCSS(ast);
      const msg = `Invalid selector ${css}`;
      this.onError(generateException(msg, SYNTAX_ERR, this.window));
      return false;
    }
    const { host } = node;
    const { branches } = walkAST(astChildren[0]);
    const [branch] = branches;
    const [...leaves] = branch;
    if (astName === 'host' && this.#evaluateHostPseudo(leaves, host, ast)) {
      return true;
    } else if (
      astName === 'host-context' &&
      this.#evaluateHostContextPseudo(leaves, host, ast)
    ) {
      return true;
    }
    return false;
  };

  /**
   * Matches pseudo-class selector.
   * @see https://html.spec.whatwg.org/_pseudo-classes
   * @param {object} ast - The AST.
   * @param {object} node - The Element node.
   * @param {object} [opt] - Options.
   * @param {boolean} [opt.forgive] - Ignores unknown or invalid selectors.
   * @param {boolean} [opt.warn] - If true, console warnings are enabled.
   * @returns {Set.<object>|boolean} A collection of matched nodes.
   */
  matchPseudoClassSelector = (ast, node, opt = {}) => {
    const { children: astChildren, name: astName } = ast;
    const { localName, parentNode } = node;
    const { forgive, warn = this.warn } = opt;
    if (Array.isArray(astChildren)) {
      // :has(), :is(), :not(), :where()
      if (KEYS_LOGICAL.has(astName)) {
        return this.#evaluateLogicalPseudo(ast, node, opt);
      }
      return this.#evaluatePseudoClassFunc(ast, node, opt);
    }
    if (KEYS_PS_NTH_OF_TYPE.has(astName)) {
      if (!parentNode) {
        return node === this.root;
      }
      const { localName, namespaceURI } = node;
      let hasPrev = false;
      let hasNext = false;
      let current = node.previousElementSibling;
      while (current) {
        if (
          current.localName === localName &&
          current.namespaceURI === namespaceURI
        ) {
          hasPrev = true;
          break;
        }
        current = current.previousElementSibling;
      }
      if (astName !== 'first-of-type') {
        current = node.nextElementSibling;
        while (current) {
          if (
            current.localName === localName &&
            current.namespaceURI === namespaceURI
          ) {
            hasNext = true;
            break;
          }
          current = current.nextElementSibling;
        }
      }
      switch (astName) {
        case 'first-of-type': {
          return !hasPrev;
        }
        case 'last-of-type': {
          return !hasNext;
        }
        case 'only-of-type':
        default: {
          return !hasPrev && !hasNext;
        }
      }
    }
    switch (astName) {
      /* Elemental pseudo-classes */
      case 'defined': {
        if (node.hasAttribute('is') || localName.includes('-')) {
          return isCustomElement(node);
        }
        return (
          node instanceof this.window.HTMLElement ||
          node instanceof this.window.SVGElement
        );
      }
      /* Element display state pseudo-classes */
      case 'open': {
        // <select> and <input type="color"> are not supported.
        return matchOpenPseudoClass(node);
      }
      case 'popover-open': {
        // FIXME: Not implemented in jsdom
        // @see https://github.com/jsdom/jsdom/issues/3721
        // return node.popover && isVisible(node);
        break;
      }
      /* Input pseudo-classes */
      case 'disabled':
      case 'enabled': {
        return this.#matchDisabledPseudoClass(astName, node);
      }
      case 'read-only':
      case 'read-write': {
        return matchReadOnlyPseudoClass(astName, node);
      }
      case 'placeholder-shown': {
        return matchPlaceholderShownPseudoClass(node, KEYS_INPUT_PLACEHOLDER);
      }
      case 'default': {
        return this.#matchDefaultPseudoClass(node);
      }
      case 'checked': {
        return matchCheckedPseudoClass(node);
      }
      case 'indeterminate': {
        return this.#matchIndeterminatePseudoClass(node);
      }
      case 'valid':
      case 'invalid': {
        return this.#matchValidityPseudoClass(astName, node);
      }
      case 'in-range':
      case 'out-of-range': {
        return matchRangePseudoClass(astName, node, KEYS_INPUT_RANGE);
      }
      case 'required':
      case 'optional': {
        return matchRequiredPseudoClass(astName, node, KEYS_INPUT_REQUIRED);
      }
      /* Location pseudo-classes */
      case 'any-link':
      case 'link': {
        return matchLinkPseudoClass(node);
      }
      case 'local-link': {
        return this.#matchLocalLinkPseudoClass(node);
      }
      case 'visited': {
        // prevent fingerprinting
        break;
      }
      case 'target': {
        return this.#matchTargetPseudoClass(node);
      }
      case 'scope': {
        if (this.node.nodeType === ELEMENT_NODE) {
          return !this.shadow && node === this.node;
        }
        return node === this.document.documentElement;
      }
      /* Tree-structural pseudo-classes */
      case 'root': {
        return node === this.document.documentElement;
      }
      case 'empty': {
        return this.#matchEmptyPseudoClass(node);
      }
      case 'first-child':
      case 'last-child':
      case 'only-child': {
        if (!parentNode) {
          return node === this.root;
        }
        if (astName === 'first-child') {
          return node === parentNode.firstElementChild;
        }
        if (astName === 'last-child') {
          return node === parentNode.lastElementChild;
        }
        return (
          node === parentNode.firstElementChild &&
          node === parentNode.lastElementChild
        );
      }
      /* User action pseudo-classes */
      case 'hover': {
        return this.#matchHoverPseudoClass(node);
      }
      case 'active': {
        return this.#matchActivePseudoClass(node);
      }
      case 'focus': {
        return this.#matchFocusPseudoClass(node);
      }
      case 'focus-visible': {
        return this.#matchFocusVisiblePseudoClass(node);
      }
      case 'focus-within': {
        return this.#matchFocusWithinPseudoClass(node);
      }
      // Ignore :host.
      case 'host': {
        break;
      }
      // Legacy pseudo-elements.
      case 'after':
      case 'before':
      case 'first-letter':
      case 'first-line': {
        if (warn) {
          this.onError(
            generateException(
              `Unsupported pseudo-element ::${astName}`,
              NOT_SUPPORTED_ERR,
              this.window
            )
          );
        }
        break;
      }
      // Not supported.
      case 'autofill':
      case 'blank':
      case 'buffering':
      case 'current':
      case 'fullscreen':
      case 'future':
      case 'has-slotted':
      case 'heading':
      case 'modal':
      case 'muted':
      case 'past':
      case 'paused':
      case 'picture-in-picture':
      case 'playing':
      case 'seeking':
      case 'stalled':
      case 'user-invalid':
      case 'user-valid':
      case 'volume-locked':
      case '-webkit-autofill': {
        if (warn) {
          this.onError(
            generateException(
              `Unsupported pseudo-class :${astName}`,
              NOT_SUPPORTED_ERR,
              this.window
            )
          );
        }
        break;
      }
      default: {
        if (astName.startsWith('-webkit-')) {
          if (warn) {
            this.onError(
              generateException(
                `Unsupported pseudo-class :${astName}`,
                NOT_SUPPORTED_ERR,
                this.window
              )
            );
          }
        } else if (!forgive) {
          this.onError(
            generateException(
              `Unknown pseudo-class :${astName}`,
              SYNTAX_ERR,
              this.window
            )
          );
        }
      }
    }
    return false;
  };

  /**
   * Evaluates the :default pseudo-class.
   * @private
   * @param {object} node - The Element node.
   * @returns {boolean} True if matched, otherwise false.
   */
  #matchDefaultPseudoClass = node => {
    const { localName } = node;
    // option
    if (localName === 'option') {
      return node.hasAttribute('selected');
    }
    const attrType = node.getAttribute('type');
    // input[type="checkbox"], input[type="radio"]
    if (
      localName === 'input' &&
      node.hasAttribute('type') &&
      node.hasAttribute('checked')
    ) {
      return KEYS_INPUT_CHECK.has(attrType);
    }
    // button[type="submit"], input[type="submit"], input[type="image"]
    if (
      (localName === 'button' &&
        !(node.hasAttribute('type') && KEYS_INPUT_RESET.has(attrType))) ||
      (localName === 'input' &&
        node.hasAttribute('type') &&
        KEYS_INPUT_SUBMIT.has(attrType))
    ) {
      let form = node.parentNode;
      while (form) {
        if (form.localName === 'form') {
          break;
        }
        form = form.parentNode;
      }
      if (form) {
        if (!this.#psDefaultCache) {
          this.#psDefaultCache = new WeakMap();
        }
        let defaultSubmit = this.#psDefaultCache.get(form);
        if (defaultSubmit === undefined) {
          const walker = this.createTreeWalker(form, { force: true });
          let refNode = traverseNode(form, walker);
          refNode = walker.firstChild();
          while (refNode) {
            const nodeName = refNode.localName;
            const nodeAttrType = refNode.getAttribute('type');
            let m;
            if (nodeName === 'button') {
              m = !(
                refNode.hasAttribute('type') &&
                KEYS_INPUT_RESET.has(nodeAttrType)
              );
            } else if (nodeName === 'input') {
              m =
                refNode.hasAttribute('type') &&
                KEYS_INPUT_SUBMIT.has(nodeAttrType);
            }
            if (m) {
              defaultSubmit = refNode;
              break;
            }
            refNode = walker.nextNode();
          }
          this.#psDefaultCache.set(form, defaultSubmit);
        }
        return defaultSubmit === node;
      }
    }
    return false;
  };

  /**
   * Evaluates the :disabled and :enabled pseudo-classes with tree-caching.
   * @private
   * @param {string} astName - The pseudo-class name ('disabled' or 'enabled').
   * @param {object} node - The Element node.
   * @returns {boolean} True if matched, otherwise false.
   */
  #matchDisabledPseudoClass = (astName, node) => {
    const { localName, parentNode } = node;
    if (
      !KEYS_FORM_PS_DISABLED.has(localName) &&
      !isCustomElement(node, { formAssociated: true })
    ) {
      return false;
    }
    if (!this.#psDisabledCache) {
      this.#psDisabledCache = new WeakSet();
    }
    if (node.disabled || node.hasAttribute('disabled')) {
      this.#psDisabledCache.add(node);
      return astName === 'disabled';
    }
    let isDisabled = false;
    if (localName === 'option') {
      if (
        parentNode &&
        parentNode.localName === 'optgroup' &&
        (parentNode.disabled || parentNode.hasAttribute('disabled'))
      ) {
        isDisabled = true;
      }
    } else if (localName !== 'optgroup') {
      let current = parentNode;
      while (current) {
        if (current.localName === 'fieldset') {
          if (current.disabled || current.hasAttribute('disabled')) {
            let legend;
            let element = current.firstElementChild;
            while (element) {
              if (element.localName === 'legend') {
                legend = element;
                break;
              }
              element = element.nextElementSibling;
            }
            if (!legend || !legend.contains(node)) {
              isDisabled = true;
              break;
            }
          }
        }
        current = current.parentNode;
      }
    }
    if (isDisabled) {
      this.#psDisabledCache.add(node);
    }
    if (astName === 'disabled') {
      return isDisabled;
    }
    return !isDisabled;
  };

  /**
   * Evaluates the :indeterminate pseudo-class.
   * @private
   * @param {object} node - The Element node.
   * @returns {boolean} True if matched, otherwise false.
   */
  #matchIndeterminatePseudoClass = node => {
    const { localName } = node;
    if (localName === 'progress') {
      return !node.hasAttribute('value');
    }
    if (localName === 'input' && node.type === 'checkbox') {
      return node.indeterminate;
    }
    if (localName === 'input' && node.type === 'radio') {
      if (node.checked || node.hasAttribute('checked')) {
        return false;
      }
      const nodeName = node.name;
      let parent = node.parentNode;
      while (parent) {
        if (parent.localName === 'form') {
          break;
        }
        parent = parent.parentNode;
      }
      if (!parent) {
        parent = this.document.documentElement;
      }
      if (!this.#psIndeterminateCache) {
        this.#psIndeterminateCache = new WeakMap();
      }
      let parentCache = this.#psIndeterminateCache.get(parent);
      if (parentCache === undefined) {
        parentCache = new Map();
        this.#psIndeterminateCache.set(parent, parentCache);
      }
      let checked = parentCache.get(nodeName);
      if (checked === undefined) {
        const walker = this.createTreeWalker(parent, { force: true });
        let refNode = traverseNode(parent, walker);
        refNode = walker.firstChild();
        while (refNode) {
          if (
            refNode.localName === 'input' &&
            refNode.getAttribute('type') === 'radio'
          ) {
            if (nodeName && refNode.getAttribute('name') === nodeName) {
              checked = !!refNode.checked;
            }
            if (checked) {
              break;
            }
          }
          refNode = walker.nextNode();
        }
        checked = !!checked;
        parentCache.set(nodeName, checked);
      }
      return !checked;
    }
    return false;
  };

  /**
   * Evaluates the :valid and :invalid pseudo-classes.
   * @private
   * @param {string} astName - The name of the pseudo-class.
   * @param {object} node - The Element node.
   * @returns {boolean} True if matched, otherwise false.
   */
  #matchValidityPseudoClass = (astName, node) => {
    const { localName } = node;
    if (KEYS_FORM_PS_VALID.has(localName)) {
      let { valid } = node.validity;
      if (node.maxLength >= 0) {
        valid = node.maxLength >= node.value.length;
      }
      if (valid && node.minLength >= 0) {
        valid = node.minLength <= node.value.length;
      }
      if (astName === 'invalid') {
        return !valid;
      }
      return valid;
    }
    if (localName === 'form' || localName === 'fieldset') {
      if (!this.#psValidCache) {
        this.#psValidCache = new WeakMap();
      }
      let valid = this.#psValidCache.get(node);
      if (valid === undefined) {
        const walker = this.createTreeWalker(node, { force: true });
        let refNode = traverseNode(node, walker);
        refNode = walker.firstChild();
        if (!refNode) {
          valid = true;
        } else {
          while (refNode) {
            if (KEYS_FORM_PS_VALID.has(refNode.localName)) {
              valid = refNode.validity.valid;
              if (refNode.maxLength >= 0) {
                valid = refNode.maxLength >= refNode.value.length;
              }
              if (valid && refNode.minLength >= 0) {
                valid = refNode.minLength <= refNode.value.length;
              }
              if (!valid) {
                break;
              }
            }
            refNode = walker.nextNode();
          }
        }
        this.#psValidCache.set(node, valid);
      }
      if (astName === 'invalid') {
        return !valid;
      }
      return valid;
    }
    return false;
  };

  /**
   * Evaluates the :local-link pseudo-class.
   * @private
   * @param {object} node - The Element node.
   * @returns {boolean} True if matched, otherwise false.
   */
  #matchLocalLinkPseudoClass = node => {
    const { localName } = node;
    if (
      (localName === 'a' || localName === 'area') &&
      node.hasAttribute('href')
    ) {
      if (!this.#documentURL) {
        this.#documentURL = new URL(this.document.URL);
      }
      const { href, origin, pathname } = this.#documentURL;
      const attrURL = new URL(node.getAttribute('href'), href);
      return attrURL.origin === origin && attrURL.pathname === pathname;
    }
    return false;
  };

  /**
   * Evaluates the :target pseudo-class.
   * @private
   * @param {object} node - The Element node.
   * @returns {boolean} True if matched, otherwise false.
   */
  #matchTargetPseudoClass = node => {
    if (!this.#documentURL) {
      this.#documentURL = new URL(this.document.URL);
    }
    const { hash } = this.#documentURL;
    return hash && hash === `#${node.id}` && this.document.contains(node);
  };

  /**
   * Evaluates the :empty pseudo-class.
   * @private
   * @param {object} node - The Element node.
   * @returns {boolean} True if matched, otherwise false.
   */
  #matchEmptyPseudoClass = node => {
    if (!node.hasChildNodes()) {
      return true;
    }
    const walker = this.createTreeWalker(node, {
      force: true,
      whatToShow: SHOW_ALL
    });
    let refNode = walker.firstChild();
    let bool;
    while (refNode) {
      bool =
        refNode.nodeType !== ELEMENT_NODE && refNode.nodeType !== TEXT_NODE;
      if (!bool) {
        break;
      }
      refNode = walker.nextSibling();
    }
    return bool;
  };

  /**
   * Evaluates the :hover pseudo-class.
   * @private
   * @param {object} node - The Element node.
   * @returns {boolean} True if matched, otherwise false.
   */
  #matchHoverPseudoClass = node => {
    const { target, type } = this.#eventHandler.currentEvent ?? {};
    return (
      /^(?:click|mouse(?:down|over|up))$/.test(type) &&
      target?.nodeType === ELEMENT_NODE &&
      node.contains(target)
    );
  };

  /**
   * Evaluates the :active pseudo-class.
   * @private
   * @param {object} node - The Element node.
   * @returns {boolean} True if matched, otherwise false.
   */
  #matchActivePseudoClass = node => {
    const { buttons, target, type } = this.#eventHandler.currentEvent ?? {};
    return (
      type === 'mousedown' &&
      buttons & 1 &&
      target?.nodeType === ELEMENT_NODE &&
      node.contains(target)
    );
  };

  /**
   * Evaluates the :focus pseudo-class.
   * @private
   * @param {object} node - The Element node.
   * @returns {boolean} True if matched, otherwise false.
   */
  #matchFocusPseudoClass = node => {
    const activeElement = this.document.activeElement;
    if (activeElement.shadowRoot) {
      const activeShadowElement = activeElement.shadowRoot.activeElement;
      let current = activeShadowElement;
      while (current) {
        if (current.nodeType === DOCUMENT_FRAGMENT_NODE) {
          const { host } = current;
          if (host === activeElement) {
            if (isFocusableArea(node)) {
              return true;
            }
            return host === node;
          }
        }
        current = current.parentNode;
      }
    }
    return node === activeElement && isFocusableArea(node);
  };

  /**
   * Evaluates the :focus-visible pseudo-class.
   * @private
   * @param {object} node - The Element node.
   * @returns {boolean} True if matched, otherwise false.
   */
  #matchFocusVisiblePseudoClass = node => {
    if (node === this.document.activeElement && isFocusableArea(node)) {
      let bool;
      if (isFocusVisible(node)) {
        bool = true;
      } else if (this.#eventHandler.currentFocus) {
        const { relatedTarget, target: focusTarget } =
          this.#eventHandler.currentFocus;
        if (focusTarget === node) {
          if (isFocusVisible(relatedTarget)) {
            bool = true;
          } else if (this.#eventHandler.currentEvent) {
            const {
              altKey: eventAltKey,
              ctrlKey: eventCtrlKey,
              key: eventKey,
              metaKey: eventMetaKey,
              target: eventTarget,
              type: eventType
            } = this.#eventHandler.currentEvent;
            // Irrelevant if eventTarget === relatedTarget
            if (eventTarget === relatedTarget) {
              if (!this.#lastFocusVisible) {
                bool = true;
              } else if (focusTarget === this.#lastFocusVisible) {
                bool = true;
              }
            } else if (eventKey === 'Tab') {
              if (
                (eventType === 'keydown' && eventTarget !== node) ||
                (eventType === 'keyup' && eventTarget === node)
              ) {
                if (eventTarget === focusTarget) {
                  if (!this.#lastFocusVisible) {
                    bool = true;
                  } else if (
                    eventTarget === this.#lastFocusVisible &&
                    relatedTarget === null
                  ) {
                    bool = true;
                  }
                } else {
                  bool = true;
                }
              }
            } else if (eventKey) {
              if (
                (eventType === 'keydown' || eventType === 'keyup') &&
                !eventAltKey &&
                !eventCtrlKey &&
                !eventMetaKey &&
                eventTarget === node
              ) {
                bool = true;
              }
            }
          } else if (
            relatedTarget === null ||
            relatedTarget === this.#lastFocusVisible
          ) {
            bool = true;
          }
        }
      }
      if (bool) {
        this.#lastFocusVisible = node;
        return bool;
      }
      if (this.#lastFocusVisible === node) {
        this.#lastFocusVisible = null;
      }
    }
    return false;
  };

  /**
   * Evaluates the :focus-within pseudo-class.
   * @private
   * @param {object} node - The Element node.
   * @returns {boolean} True if matched, otherwise false.
   */
  #matchFocusWithinPseudoClass = node => {
    if (!this.#focusWithinCache) {
      this.#focusWithinCache = new Set();
      let currentFocus = this.document.activeElement;
      while (currentFocus?.shadowRoot?.activeElement) {
        currentFocus = currentFocus.shadowRoot.activeElement;
      }
      if (currentFocus && isFocusableArea(currentFocus)) {
        while (currentFocus) {
          this.#focusWithinCache.add(currentFocus);
          if (currentFocus.parentNode) {
            currentFocus = currentFocus.parentNode;
          } else if (
            currentFocus.nodeType === DOCUMENT_FRAGMENT_NODE &&
            currentFocus.host
          ) {
            currentFocus = currentFocus.host;
          } else {
            break;
          }
        }
      }
    }
    return this.#focusWithinCache.has(node);
  };

  /**
   * Creates a TreeWalker.
   * @param {object} node - The Document, DocumentFragment, or Element node.
   * @param {object} [opt] - Options.
   * @param {boolean} [opt.force] - Force creation of a new TreeWalker.
   * @param {number} [opt.whatToShow] - The NodeFilter whatToShow value.
   * @returns {object} The TreeWalker object.
   */
  createTreeWalker = (node, opt = {}) => {
    const { force = false, whatToShow = SHOW_CONTAINER } = opt;
    if (force) {
      return this.document.createTreeWalker(node, whatToShow);
    }
    if (!this.#walkers) {
      this.#walkers = new WeakMap();
    }
    let walker = this.#walkers.get(node);
    if (walker) {
      return walker;
    }
    walker = this.document.createTreeWalker(node, whatToShow);
    this.#walkers.set(node, walker);
    return walker;
  };

  /**
   * Yields combinator matches (Lazy evaluation, O(1) memory).
   * @param {object} twig - The twig object.
   * @param {object} node - The Element node.
   * @param {object} [opt] - Options.
   * @param {string} [opt.dir] - The find direction.
   * @yields {object} The matched node.
   */
  *yieldCombinatorMatches(twig, node, opt = {}) {
    const {
      combo: { name: comboName },
      leaves
    } = twig;
    const { dir } = opt;
    switch (comboName) {
      case '+': {
        const refNode =
          dir === DIR_NEXT
            ? node.nextElementSibling
            : node.previousElementSibling;
        if (refNode && this.matchLeaves(leaves, refNode, opt)) {
          yield refNode;
        }
        break;
      }
      case '~': {
        let refNode =
          dir === DIR_NEXT
            ? node.nextElementSibling
            : node.previousElementSibling;
        while (refNode) {
          if (this.matchLeaves(leaves, refNode, opt)) {
            yield refNode;
          }
          refNode =
            dir === DIR_NEXT
              ? refNode.nextElementSibling
              : refNode.previousElementSibling;
        }
        break;
      }
      case '>': {
        if (dir === DIR_NEXT) {
          let refNode = node.firstElementChild;
          while (refNode) {
            if (this.matchLeaves(leaves, refNode, opt)) {
              yield refNode;
            }
            refNode = refNode.nextElementSibling;
          }
        } else {
          const { parentNode } = node;
          if (parentNode && this.matchLeaves(leaves, parentNode, opt)) {
            yield parentNode;
          }
        }
        break;
      }
      case ' ':
      default: {
        if (dir === DIR_NEXT) {
          for (const refNode of this.yieldFindDescendantNodes(
            leaves,
            node,
            opt
          )) {
            yield refNode;
          }
        } else {
          const ancestors = [];
          let refNode = node.parentNode;
          while (refNode) {
            if (this.matchLeaves(leaves, refNode, opt)) {
              ancestors.push(refNode);
            }
            refNode = refNode.parentNode;
          }
          if (ancestors.length) {
            for (let i = ancestors.length - 1; i >= 0; i--) {
              yield ancestors[i];
            }
          }
        }
      }
    }
  }

  /**
   * Traverses all descendant nodes and yields matches.
   * @param {object} baseNode - The base Element node or Element.shadowRoot.
   * @param {Array.<object>} leaves - The AST leaves.
   * @param {object} opt - Options.
   * @yields {object} The matched node.
   */
  *yieldTraverseAllDescendants(baseNode, leaves, opt) {
    const walker = this.createTreeWalker(baseNode);
    traverseNode(baseNode, walker);
    let currentNode = walker.firstChild();
    while (currentNode) {
      if (this.matchLeaves(leaves, currentNode, opt)) {
        yield currentNode;
      }
      currentNode = walker.nextNode();
    }
  }

  /**
   * Finds descendant nodes and yields matches.
   * @param {Array.<object>} leaves - The AST leaves.
   * @param {object} baseNode - The base Element node or Element.shadowRoot.
   * @param {object} opt - Options.
   * @yields {object} The matched node.
   */
  *yieldFindDescendantNodes(leaves, baseNode, opt) {
    const [{ name, type: leafType }] = leaves;
    const leafName = unescapeSelector(name);
    const filterLeaves = this.getFilterLeaves(leaves);
    const isSimple = filterLeaves.length === 0;
    switch (leafType) {
      case ID_SELECTOR: {
        if (
          !this.shadow &&
          baseNode.nodeType === ELEMENT_NODE &&
          this.root.nodeType !== ELEMENT_NODE
        ) {
          const foundNode = this.root.getElementById(leafName);
          if (
            foundNode &&
            foundNode !== baseNode &&
            baseNode.contains(foundNode)
          ) {
            if (isSimple || this.matchLeaves(filterLeaves, foundNode, opt)) {
              yield foundNode;
            }
          }
          return;
        }
        break;
      }
      case CLASS_SELECTOR: {
        if (typeof baseNode.getElementsByClassName === 'function') {
          const collection = baseNode.getElementsByClassName(leafName);
          for (let i = 0, len = collection.length; i < len; i++) {
            const foundNode = collection[i];
            if (isSimple || this.matchLeaves(filterLeaves, foundNode, opt)) {
              yield foundNode;
            }
          }
          return;
        }
        break;
      }
      case TYPE_SELECTOR: {
        if (
          typeof baseNode.getElementsByTagName === 'function' &&
          !leafName.includes('|')
        ) {
          const collection = baseNode.getElementsByTagName(leafName);
          for (let i = 0, len = collection.length; i < len; i++) {
            const foundNode = collection[i];
            if (isSimple || this.matchLeaves(filterLeaves, foundNode, opt)) {
              yield foundNode;
            }
          }
          return;
        }
        break;
      }
      case PS_ELEMENT_SELECTOR: {
        matchPseudoElementSelector(leafName, leafType, opt);
        return;
      }
      default: {
        // no-op
      }
    }
    yield* this.yieldTraverseAllDescendants(baseNode, leaves, opt);
  }

  /**
   * Gets selector branches from cache or parses them.
   * @private
   * @param {object} selector - The AST.
   * @returns {Array.<Array.<object>>} The selector branches.
   */
  #getSelectorBranches = selector => {
    let branches = this.#astCache.get(selector);
    if (branches) {
      return branches;
    }
    const walkedResult = walkAST(selector);
    branches = walkedResult.branches;
    this.#astCache.set(selector, branches);
    return branches;
  };

  /**
   * Checks if a node matches any of the given selector branches.
   * @private
   * @param {Array.<Array.<object>>} branches - The selector branches to test.
   * @param {object} node - The element node to match against.
   * @param {object} [opt] - Optional parameters.
   * @returns {boolean} True if any branch matches, otherwise false.
   */
  #filterNthChildOfSelectorBranches = (branches, node, opt) => {
    let filterMatch = false;
    for (const branch of branches) {
      if (this.matchLeaves(branch, node, opt)) {
        filterMatch = true;
        break;
      }
    }
    return filterMatch;
  };

  /**
   * Evaluates An+B mathematically.
   * @private
   * @param {object} ast - The AST.
   * @param {object} node - The Element node.
   * @param {string} nthName - The name of the nth pseudo-class.
   * @param {object} opt - Options.
   * @returns {boolean} True if matches, otherwise false.
   */
  #matchAnPlusB = (ast, node, nthName, opt) => {
    const { parentNode } = node;
    if (!parentNode && node !== this.root) {
      return false;
    }
    if (!this.#anbCache) {
      this.#anbCache = new WeakMap();
    }
    let anb = this.#anbCache.get(ast);
    if (anb === undefined) {
      const {
        nth: { a, b, name: nthIdentName },
        selector
      } = ast;
      anb = {
        a: 0,
        b: 0,
        isLast: nthName.includes('last'),
        isOfType: nthName.includes('of-type'),
        selector: null
      };
      if (nthIdentName) {
        if (nthIdentName === 'even') {
          anb.a = 2;
          anb.b = 0;
        } else if (nthIdentName === 'odd') {
          anb.a = 2;
          anb.b = 1;
        }
      } else {
        const intA = parseInt(a);
        if (Number.isInteger(intA)) {
          anb.a = intA;
        }
        const intB = parseInt(b);
        if (Number.isInteger(intB)) {
          anb.b = intB;
        }
      }
      if (selector && /^nth-(?:last-)?child$/.test(nthName)) {
        anb.selector = selector;
      }
      this.#anbCache.set(ast, anb);
    }
    const { a, b, isLast, isOfType, selector: anbSelector } = anb;
    let pos;
    if (!parentNode) {
      if (anbSelector) {
        const selectorBranches = this.#getSelectorBranches(anbSelector);
        if (
          !this.#filterNthChildOfSelectorBranches(selectorBranches, node, opt)
        ) {
          return false;
        }
      }
      pos = 1;
    } else {
      if (!this.#nthIndexCache) {
        this.#nthIndexCache = new WeakMap();
      }
      let parentCache = this.#nthIndexCache.get(parentNode);
      if (parentCache === undefined) {
        parentCache = new Map();
        this.#nthIndexCache.set(parentNode, parentCache);
      }
      let indexMap = parentCache.get(ast);
      if (indexMap === undefined) {
        indexMap = new Map();
        parentCache.set(ast, indexMap);
        let currentPos = 1;
        let current = isLast
          ? parentNode.lastElementChild
          : parentNode.firstElementChild;
        if (anbSelector) {
          const selectorBranches = this.#getSelectorBranches(anbSelector);
          while (current) {
            if (
              this.#filterNthChildOfSelectorBranches(
                selectorBranches,
                current,
                opt
              )
            ) {
              indexMap.set(current, currentPos++);
            }
            current = isLast
              ? current.previousElementSibling
              : current.nextElementSibling;
          }
        } else {
          const typeCounts = new Map();
          while (current) {
            if (isOfType) {
              const typeKey = `${current.localName}|${current.namespaceURI}`;
              const tPos = (typeCounts.get(typeKey) || 0) + 1;
              typeCounts.set(typeKey, tPos);
              indexMap.set(current, tPos);
            } else {
              indexMap.set(current, currentPos++);
            }
            current = isLast
              ? current.previousElementSibling
              : current.nextElementSibling;
          }
        }
      }
      pos = indexMap.get(node);
      if (pos === undefined) {
        return false;
      }
    }
    if (a === 0) {
      return pos === b;
    }
    const diff = pos - b;
    if (diff % a !== 0) {
      return false;
    }
    return a > 0 ? diff >= 0 : diff <= 0;
  };

  /**
   * Evaluates if any combinator match satisfies the condition to short-circuit.
   * @private
   * @param {object} twig - The AST twig object.
   * @param {object} node - The element node.
   * @param {Array.<object>} remainingLeaves - The remaining AST leaves.
   * @param {object} opt - The match options.
   * @returns {boolean} True if matched, otherwise false.
   */
  #hasCombinatorMatch = (twig, node, remainingLeaves, opt) => {
    const {
      combo: { name: comboName },
      leaves
    } = twig;
    const isLast = remainingLeaves.length === 0;
    // Check if the target node satisfies the leaves and remaining conditions.
    const checkNode = refNode => {
      if (this.matchLeaves(leaves, refNode, opt)) {
        if (isLast) {
          return true;
        }
        if (this.#matchHasPseudoFunc(remainingLeaves, refNode, opt)) {
          return true;
        }
      }
      return false;
    };
    switch (comboName) {
      case '+': {
        const refNode = node.nextElementSibling;
        return refNode ? checkNode(refNode) : false;
      }
      case '~': {
        let refNode = node.nextElementSibling;
        while (refNode) {
          if (checkNode(refNode)) {
            return true;
          }
          refNode = refNode.nextElementSibling;
        }
        return false;
      }
      case '>': {
        // Direct children only
        let refNode = node.firstElementChild;
        while (refNode) {
          if (checkNode(refNode)) {
            return true;
          }
          refNode = refNode.nextElementSibling;
        }
        return false;
      }
      case ' ':
      default: {
        const [leaf] = leaves;
        const filterLeaves = this.getFilterLeaves(leaves);
        // ID
        if (
          leaf.type === ID_SELECTOR &&
          !this.shadow &&
          node.nodeType === ELEMENT_NODE &&
          this.root.nodeType !== ELEMENT_NODE
        ) {
          const leafName = unescapeSelector(leaf.name);
          const foundNode = this.root.getElementById(leafName);
          if (foundNode && foundNode !== node && node.contains(foundNode)) {
            // Only check filter leaves if it's a compound selector
            if (
              filterLeaves.length === 0 ||
              this.matchLeaves(filterLeaves, foundNode, opt)
            ) {
              if (isLast) {
                return true;
              }
              if (this.#matchHasPseudoFunc(remainingLeaves, foundNode, opt)) {
                return true;
              }
            }
          }
          return false;
        }
        // Class
        if (
          leaf.type === CLASS_SELECTOR &&
          typeof node.getElementsByClassName === 'function'
        ) {
          const leafName = unescapeSelector(leaf.name);
          const collection = node.getElementsByClassName(leafName);
          for (let i = 0, len = collection.length; i < len; i++) {
            const refNode = collection[i];
            // Apply filter before calling the expensive checkNode
            if (
              filterLeaves.length === 0 ||
              this.matchLeaves(filterLeaves, refNode, opt)
            ) {
              if (isLast) {
                return true;
              }
              if (this.#matchHasPseudoFunc(remainingLeaves, refNode, opt)) {
                return true;
              }
            }
          }
          return false;
        }
        // Type
        if (
          leaf.type === TYPE_SELECTOR &&
          typeof node.getElementsByTagName === 'function' &&
          !leaf.name.includes('|')
        ) {
          const leafName = unescapeSelector(leaf.name);
          const collection = node.getElementsByTagName(leafName);
          for (let i = 0, len = collection.length; i < len; i++) {
            const refNode = collection[i];
            // Apply filter before calling the expensive checkNode
            if (
              filterLeaves.length === 0 ||
              this.matchLeaves(filterLeaves, refNode, opt)
            ) {
              if (isLast) {
                return true;
              }
              if (this.#matchHasPseudoFunc(remainingLeaves, refNode, opt)) {
                return true;
              }
            }
          }
          return false;
        }
        // TreeWalker (for pseudo-elements, attributes, etc.)
        const walker = this.createTreeWalker(node);
        traverseNode(node, walker);
        let currentNode = walker.firstChild();
        while (currentNode) {
          if (checkNode(currentNode)) {
            return true;
          }
          currentNode = walker.nextNode();
        }
        return false;
      }
    }
  };

  /**
   * Matches the :has() pseudo-class function.
   * @private
   * @param {Array.<object>} astLeaves - The AST leaves.
   * @param {object} node - The Element node.
   * @param {object} [opt] - Options.
   * @returns {boolean} True if matched, otherwise false.
   */
  #matchHasPseudoFunc = (astLeaves, node, opt = {}) => {
    let combo;
    let startIndex = 0;
    if (astLeaves[0].type === COMBINATOR) {
      combo = astLeaves[0];
      startIndex = 1;
    } else {
      combo = { name: ' ', type: COMBINATOR };
      startIndex = 0;
    }
    const twigLeaves = [];
    const l = astLeaves.length;
    let nextComboIndex = startIndex;
    for (; nextComboIndex < l; nextComboIndex++) {
      if (astLeaves[nextComboIndex].type === COMBINATOR) {
        break;
      }
      twigLeaves.push(astLeaves[nextComboIndex]);
    }
    const twig = { combo, leaves: twigLeaves };
    opt.dir = DIR_NEXT;
    const remainingLeaves = astLeaves.slice(nextComboIndex);
    return this.#hasCombinatorMatch(twig, node, remainingLeaves, opt);
  };

  /**
   * Builds an Allowlist for the :has() branch using a sparse seed element.
   * @private
   * @param {Array} leaves - The AST leaves of the selector branch.
   * @returns {object|null} The wrapper object containing the WeakSet, or null.
   */
  #buildHasAllowlist = leaves => {
    const { seed } = findBestSeed(leaves);
    if (!seed) {
      return null;
    }
    if (this.shadow || this.node.nodeType === DOCUMENT_FRAGMENT_NODE) {
      return null;
    }
    let seedElements = null;
    let isSingleNode = false;
    if (seed.type === 'id') {
      if (typeof this.root.getElementById === 'function') {
        const node = this.root.getElementById(seed.value);
        if (node) {
          seedElements = node;
          isSingleNode = true;
        }
      }
    } else if (seed.type === 'class') {
      if (typeof this.root.getElementsByClassName === 'function') {
        seedElements = this.root.getElementsByClassName(seed.value);
      }
    } else if (seed.type === 'tag') {
      if (typeof this.root.getElementsByTagName === 'function') {
        seedElements = this.root.getElementsByTagName(seed.value);
      }
    }
    if (!seedElements) {
      return null;
    }
    const len = isSingleNode ? 1 : seedElements.length;
    if (len === 0 || len > HEX * HEX) {
      return null;
    }
    const filterResult = {
      seeded: true,
      set: new WeakSet()
    };
    const list = filterResult.set;
    const visitedAncestors = new Set();
    if (this.node) {
      list.add(this.node);
    }
    for (let i = 0; i < len; i++) {
      const current = isSingleNode ? seedElements : seedElements[i];
      if (current) {
        populateHasAllowlist(current, list, visitedAncestors);
      }
    }
    return filterResult;
  };

  /**
   * Evaluates :has() pseudo-class.
   * @private
   * @param {object} astData - The AST data.
   * @param {object} node - The Element node.
   * @param {object} [opt] - Options.
   * @returns {?object} The matched node.
   */
  #evaluateHasPseudo = (astData, node, opt = {}) => {
    const { branches } = astData;
    let bool = false;
    if (!this.#psHasFilterCache) {
      this.#psHasFilterCache = new WeakMap();
    }
    let rootCache = this.#psHasFilterCache.get(this.root);
    if (rootCache === undefined) {
      rootCache = new WeakMap();
      this.#psHasFilterCache.set(this.root, rootCache);
    }
    for (const leaves of branches) {
      if (!rootCache.has(leaves)) {
        const filterResult = this.#buildHasAllowlist(leaves);
        rootCache.set(leaves, filterResult);
      }
      const allowlist = rootCache.get(leaves);
      if (
        allowlist &&
        allowlist.seeded &&
        node.nodeType !== DOCUMENT_FRAGMENT_NODE &&
        !allowlist.set.has(node)
      ) {
        continue;
      }
      bool = this.#matchHasPseudoFunc(leaves, node, opt);
      if (bool) {
        break;
      }
    }
    if (!bool) {
      return null;
    }
    if (
      (opt.isShadowRoot || this.shadow) &&
      node.nodeType === DOCUMENT_FRAGMENT_NODE
    ) {
      return this.#verifyShadowHost ? node : null;
    }
    return node;
  };

  /**
   * Retrieves a cleared Set from the pool.
   * @private
   * @returns {Set.<object>} A cleared Set instance.
   */
  #acquireSet = () => {
    if (this.#setPoolIndex === this.#setPool.length) {
      this.#setPool.push(new Set());
    }
    const set = this.#setPool[this.#setPoolIndex++];
    set.clear();
    return set;
  };

  /**
   * Matches logical pseudo-class functions.
   * @private
   * @param {object} astData - The AST data.
   * @param {object} node - The Element node.
   * @param {object} [opt] - Options.
   * @returns {boolean} True if matches, otherwise false.
   */
  #matchLogicalPseudoFunc = (astData, node, opt = {}) => {
    const { astName, isInvalidShadow, twigBranches } = astData;
    // Handle :has().
    if (astName === 'has') {
      return this.#evaluateHasPseudo(astData, node, opt) === node;
    }
    // Check for shadow root.
    const isShadowRoot =
      (opt.isShadowRoot || this.shadow) &&
      node.nodeType === DOCUMENT_FRAGMENT_NODE;
    if (isShadowRoot && isInvalidShadow) {
      return false;
    }
    // Handle :is(), :not(), and :where().
    const prevForgive = opt.forgive;
    const prevDir = opt.dir;
    opt.forgive = astName === 'is' || astName === 'where';
    opt.dir = undefined;
    const l = twigBranches.length;
    let bool = false;
    for (let i = 0; i < l; i++) {
      const branch = twigBranches[i];
      const lastIndex = branch.length - 1;
      const { leaves } = branch[lastIndex];
      bool = this.matchLeaves(leaves, node, opt);
      if (bool && lastIndex > 0) {
        const initialPoolIndex = this.#setPoolIndex;
        let currentNodes = this.#acquireSet();
        currentNodes.add(node);
        for (let j = lastIndex - 1; j >= 0; j--) {
          const twig = branch[j];
          const isLastStep = j === 0;
          const nextNodes = isLastStep ? null : this.#acquireSet();
          let hasMatch = false;
          opt.dir = DIR_PREV;
          for (const nextNode of currentNodes) {
            for (const matchedNode of this.yieldCombinatorMatches(
              twig,
              nextNode,
              opt
            )) {
              hasMatch = true;
              if (isLastStep) {
                break;
              }
              nextNodes.add(matchedNode);
            }
            if (isLastStep && hasMatch) {
              break;
            }
          }
          if (!hasMatch) {
            bool = false;
            break;
          }
          if (isLastStep) {
            bool = true;
          } else {
            currentNodes = nextNodes;
          }
        }
        this.#setPoolIndex = initialPoolIndex;
      }
      if (bool) {
        break;
      }
    }
    opt.forgive = prevForgive;
    opt.dir = prevDir;
    if (astName === 'not') {
      return !bool;
    }
    return bool;
  };

  /**
   * Evaluates logical pseudo-class selector.
   * @private
   * @param {object} ast - The AST.
   * @param {object} node - The Element node.
   * @param {object} [opt] - Options.
   * @param {boolean} [opt.forgive] - Ignores unknown or invalid selectors.
   * @param {boolean} [opt.warn] - If true, console warnings are enabled.
   * @returns {boolean} True if matches, otherwise false.
   */
  #evaluateLogicalPseudo = (ast, node, opt = {}) => {
    const { children: astChildren, name: astName } = ast;
    if (!astChildren.length && astName !== 'is' && astName !== 'where') {
      const css = generateCSS(ast);
      const msg = `Invalid selector ${css}`;
      this.onError(generateException(msg, SYNTAX_ERR, this.window));
      return false;
    }
    const cachedAstData = this.#astCache.get(ast);
    if (cachedAstData) {
      return this.#matchLogicalPseudoFunc(cachedAstData, node, opt);
    }
    const { branches } = walkAST(ast);
    if (astName === 'has') {
      const astData = { astName, branches };
      this.#astCache.set(ast, astData);
      return this.#matchLogicalPseudoFunc(astData, node, opt);
    }
    let isInvalidShadow = false;
    const twigBranches = [];
    const l = branches.length;
    for (let i = 0; i < l; i++) {
      const leaves = branches[i];
      const branch = [];
      const leavesSet = new Set();
      const leavesLen = leaves.length;
      if (!isInvalidShadow && astName !== 'has') {
        if (leavesLen > 1) {
          isInvalidShadow = true;
        } else if (astName === 'not') {
          const [{ type: childAstType }] = leaves;
          if (childAstType !== PS_CLASS_SELECTOR) {
            isInvalidShadow = true;
          }
        }
      }
      for (let j = 0; j < leavesLen; j++) {
        const item = leaves[j];
        if (item.type === COMBINATOR) {
          branch.push({
            combo: item,
            leaves: [...leavesSet]
          });
          leavesSet.clear();
        } else {
          leavesSet.add(item);
        }
        if (j === leavesLen - 1) {
          branch.push({
            combo: null,
            leaves: [...leavesSet]
          });
          leavesSet.clear();
        }
      }
      twigBranches.push(branch);
    }
    const astData = {
      astName,
      isInvalidShadow,
      twigBranches
    };
    this.#astCache.set(ast, astData);
    return this.#matchLogicalPseudoFunc(astData, node, opt);
  };

  /**
   * Evaluates pseudo-class function.
   * @private
   * @see https://html.spec.whatwg.org/_pseudo-classes
   * @param {object} ast - The AST.
   * @param {object} node - The Element node.
   * @param {object} [opt] - Options.
   * @param {boolean} [opt.forgive] - Ignores unknown or invalid selectors.
   * @param {boolean} [opt.warn] - If true, console warnings are enabled.
   * @returns {boolean} True if matches, otherwise false.
   */
  #evaluatePseudoClassFunc = (ast, node, opt = {}) => {
    const { children: astChildren, name: astName } = ast;
    const { forgive, warn = this.warn } = opt;
    // :nth-child(), :nth-last-child(), nth-of-type(), :nth-last-of-type()
    if (/^nth-(?:last-)?(?:child|of-type)$/.test(astName)) {
      if (astChildren.length !== 1) {
        const css = generateCSS(ast);
        this.onError(
          generateException(`Invalid selector ${css}`, SYNTAX_ERR, this.window)
        );
        return false;
      }
      const [branch] = astChildren;
      return this.#matchAnPlusB(branch, node, astName, opt);
    }
    switch (astName) {
      // :dir()
      case 'dir': {
        if (astChildren.length !== 1) {
          const css = generateCSS(ast);
          this.onError(
            generateException(
              `Invalid selector ${css}`,
              SYNTAX_ERR,
              this.window
            )
          );
          return false;
        }
        const [astChild] = astChildren;
        if (!this.#psDirCache) {
          this.#psDirCache = new WeakMap();
        }
        const res = matchDirectionPseudoClass(astChild, node, this.#psDirCache);
        if (res) {
          return true;
        }
        break;
      }
      // :lang()
      case 'lang': {
        if (!astChildren.length) {
          const css = generateCSS(ast);
          this.onError(
            generateException(
              `Invalid selector ${css}`,
              SYNTAX_ERR,
              this.window
            )
          );
          return false;
        }
        if (!this.#psLangCache) {
          this.#psLangCache = new WeakMap();
        }
        let bool;
        for (const astChild of astChildren) {
          bool = matchLanguagePseudoClass(astChild, node, this.#psLangCache);
          if (bool) {
            break;
          }
        }
        if (bool) {
          return true;
        }
        break;
      }
      // :state()
      case 'state': {
        if (isCustomElement(node)) {
          const [{ value: stateValue }] = astChildren;
          if (stateValue) {
            if (node[stateValue]) {
              return true;
            }
            for (const i in node) {
              const prop = node[i];
              if (prop instanceof this.window.ElementInternals) {
                if (prop?.states?.has(stateValue)) {
                  return true;
                }
                break;
              }
            }
          }
        }
        break;
      }
      case 'current':
      case 'heading':
      case 'nth-col':
      case 'nth-last-col': {
        if (warn) {
          this.onError(
            generateException(
              `Unsupported pseudo-class :${astName}()`,
              NOT_SUPPORTED_ERR,
              this.window
            )
          );
        }
        break;
      }
      // Ignore :host() and :host-context().
      case 'host':
      case 'host-context': {
        break;
      }
      // Deprecated in CSS Selectors 3.
      case 'contains': {
        if (warn) {
          this.onError(
            generateException(
              `Unknown pseudo-class :${astName}()`,
              NOT_SUPPORTED_ERR,
              this.window
            )
          );
        }
        break;
      }
      default: {
        if (!forgive) {
          this.onError(
            generateException(
              `Unknown pseudo-class :${astName}()`,
              SYNTAX_ERR,
              this.window
            )
          );
        }
      }
    }
    return false;
  };

  /**
   * Evaluates the :host() pseudo-class.
   * @private
   * @param {Array.<object>} leaves - The AST leaves.
   * @param {object} host - The host element.
   * @param {object} ast - The original AST for error reporting.
   * @returns {boolean} True if matches, otherwise false.
   */
  #evaluateHostPseudo = (leaves, host, ast) => {
    const l = leaves.length;
    for (let i = 0; i < l; i++) {
      const leaf = leaves[i];
      if (leaf.type === COMBINATOR) {
        const css = generateCSS(ast);
        const msg = `Invalid selector ${css}`;
        this.onError(generateException(msg, SYNTAX_ERR, this.window));
        return false;
      }
      if (!this.matchSelector(leaf, host)) {
        return false;
      }
    }
    return true;
  };

  /**
   * Evaluates the :host-context() pseudo-class.
   * @private
   * @param {Array.<object>} leaves - The AST leaves.
   * @param {object} host - The host element.
   * @param {object} ast - The original AST for error reporting.
   * @returns {boolean} True if matched.
   */
  #evaluateHostContextPseudo = (leaves, host, ast) => {
    let parent = host;
    while (parent) {
      let bool;
      const l = leaves.length;
      for (let i = 0; i < l; i++) {
        const leaf = leaves[i];
        if (leaf.type === COMBINATOR) {
          const css = generateCSS(ast);
          const msg = `Invalid selector ${css}`;
          this.onError(generateException(msg, SYNTAX_ERR, this.window));
          return false;
        }
        bool = this.matchSelector(leaf, parent);
        if (!bool) {
          break;
        }
      }
      if (bool) {
        return true;
      }
      parent = parent.parentNode;
    }
    return false;
  };

  /**
   * Matches a selector for element nodes.
   * @private
   * @param {object} ast - The AST.
   * @param {object} node - The Element node.
   * @param {object} opt - Options.
   * @returns {boolean} True if matches, otherwise false.
   */
  #matchSelectorForElement = (ast, node, opt) => {
    const { type: astType } = ast;
    switch (astType) {
      case ATTR_SELECTOR: {
        return matchAttributeSelector(ast, node, opt);
      }
      case ID_SELECTOR: {
        return node.id === unescapeSelector(ast.name);
      }
      case CLASS_SELECTOR: {
        const astName = unescapeSelector(ast.name);
        return node.classList.contains(astName);
      }
      case NEST_SELECTOR: {
        const nestingAST = parseSelector(':scope', 'selector');
        return this.matchPseudoClassSelector(
          nestingAST.children.head.data,
          node,
          opt
        );
      }
      case PS_CLASS_SELECTOR: {
        return this.matchPseudoClassSelector(ast, node, opt);
      }
      case TYPE_SELECTOR: {
        return matchTypeSelector(ast, node, opt);
      }
      // PS_ELEMENT_SELECTOR is handled by default.
      default: {
        try {
          if (this.check) {
            const css = generateCSS(ast);
            this.pseudoElements.push(css);
            return true;
          } else {
            const astName = unescapeSelector(ast.name);
            matchPseudoElementSelector(astName, astType, opt);
          }
        } catch (e) {
          this.onError(e);
        }
      }
    }
    return false;
  };

  /**
   * Matches a selector for a shadow root.
   * @private
   * @param {object} ast - The AST.
   * @param {object} node - The DocumentFragment node.
   * @param {object} [opt] - Options.
   * @returns {boolean} True if matches, otherwise false.
   */
  #matchSelectorForShadowRoot = (ast, node, opt = {}) => {
    const { name: astName } = ast;
    if (KEYS_LOGICAL.has(astName)) {
      opt.isShadowRoot = true;
      return this.matchPseudoClassSelector(ast, node, opt);
    }
    if (astName === 'host' || astName === 'host-context') {
      const matches = this.evaluateShadowHost(ast, node, opt);
      if (matches) {
        this.#verifyShadowHost = true;
        return true;
      }
    }
    return false;
  };
}
