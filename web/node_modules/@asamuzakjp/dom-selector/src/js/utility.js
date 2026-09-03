/**
 * utility.js
 */

/* import */
import bidiFactory from 'bidi-js';
import isCustomElementName from 'is-potential-custom-element-name';

/* constants */
import {
  CLASS_SELECTOR,
  DIR_NEXT,
  DIR_PREV,
  DOCUMENT_FRAGMENT_NODE,
  DOCUMENT_NODE,
  DOCUMENT_POSITION_CONTAINS,
  DOCUMENT_POSITION_PRECEDING,
  ELEMENT_NODE,
  ID_SELECTOR,
  INPUT_BUTTON,
  INPUT_EDIT,
  INPUT_LTR,
  INPUT_TEXT,
  PS_ELEMENT_SELECTOR,
  SHOW_ELEMENT,
  TARGET_FIRST,
  TEXT_NODE,
  TYPE_FROM,
  TYPE_SELECTOR,
  TYPE_TO
} from './constant.js';
const KEYS_DIR_AUTO = new Set([...INPUT_BUTTON, ...INPUT_TEXT, 'hidden']);
const KEYS_DIR_LTR = new Set(INPUT_LTR);
const KEYS_INPUT_EDIT = new Set(INPUT_EDIT);
const KEYS_NODE_DIR_EXCLUDE = new Set(['bdi', 'script', 'style', 'textarea']);
const KEYS_NODE_FOCUSABLE = new Set(['button', 'select', 'textarea']);
const KEYS_NODE_FOCUSABLE_SVG = new Set([
  'clipPath',
  'defs',
  'desc',
  'linearGradient',
  'marker',
  'mask',
  'metadata',
  'pattern',
  'radialGradient',
  'script',
  'style',
  'symbol',
  'title'
]);

/* regexp */
const REG_IS_HTML = /^(?:application\/xhtml\+x|text\/ht)ml$/;
const REG_IS_XML =
  /^(?:application\/(?:[\w\-.]+\+)?|image\/[\w\-.]+\+|text\/)xml$/;

/**
 * Get type of an object.
 * @param {object} o - Object to check.
 * @returns {string} - Type of the object.
 */
export const getType = o =>
  Object.prototype.toString.call(o).slice(TYPE_FROM, TYPE_TO);

/**
 * Verify array contents.
 * @param {Array} arr - The array.
 * @param {string} type - Expected type, e.g. 'String'.
 * @throws {TypeError} - Throws if array or its items are of unexpected type.
 * @returns {Array} - The verified array.
 */
export const verifyArray = (arr, type) => {
  if (!Array.isArray(arr)) {
    throw new TypeError(`Unexpected type ${getType(arr)}`);
  }
  if (typeof type !== 'string') {
    throw new TypeError(`Unexpected type ${getType(type)}`);
  }
  for (const item of arr) {
    if (getType(item) !== type) {
      throw new TypeError(`Unexpected type ${getType(item)}`);
    }
  }
  return arr;
};

/**
 * Generate a DOMException.
 * @param {string} msg - The error message.
 * @param {string} name - The error name.
 * @param {object} globalObject - The global object (e.g., window).
 * @returns {DOMException} The generated DOMException object.
 */
export const generateException = (msg, name, globalObject = globalThis) => {
  return new globalObject.DOMException(msg, name);
};

/**
 * Resolve content document, root node, and check if it's in a shadow DOM.
 * @param {object} node - Document, DocumentFragment, or Element node.
 * @returns {Array.<object|boolean>} - [document, root, isInShadow].
 */
export const resolveContent = node => {
  if (!node?.nodeType) {
    throw new TypeError(`Unexpected type ${getType(node)}`);
  }
  let document;
  let root;
  let shadow;
  switch (node.nodeType) {
    case DOCUMENT_NODE: {
      document = node;
      root = node;
      break;
    }
    case DOCUMENT_FRAGMENT_NODE: {
      const { host, mode, ownerDocument } = node;
      document = ownerDocument;
      root = node;
      shadow = host && (mode === 'close' || mode === 'open');
      break;
    }
    case ELEMENT_NODE: {
      document = node.ownerDocument;
      let refNode = node;
      while (refNode) {
        const { host, mode, nodeType, parentNode } = refNode;
        if (nodeType === DOCUMENT_FRAGMENT_NODE) {
          shadow = host && (mode === 'close' || mode === 'open');
          break;
        } else if (parentNode) {
          refNode = parentNode;
        } else {
          break;
        }
      }
      root = refNode;
      break;
    }
    default: {
      throw new TypeError(`Unexpected node ${node.nodeName}`);
    }
  }
  return [document, root, !!shadow];
};

/**
 * Traverse node tree with a TreeWalker.
 * @param {object} node - The target node.
 * @param {object} walker - The TreeWalker instance.
 * @param {boolean} [force] - Traverse only to the next node.
 * @returns {?object} - The current node if found, otherwise null.
 */
export const traverseNode = (node, walker, force = false) => {
  if (!node?.nodeType) {
    throw new TypeError(`Unexpected type ${getType(node)}`);
  }
  if (!walker) {
    return null;
  }
  let refNode = walker.currentNode;
  if (refNode === node) {
    return refNode;
  } else if (force || refNode.contains(node)) {
    refNode = walker.nextNode();
    while (refNode) {
      if (refNode === node) {
        break;
      }
      refNode = walker.nextNode();
    }
    return refNode;
  } else {
    if (refNode !== walker.root) {
      let bool;
      while (refNode) {
        if (refNode === node) {
          bool = true;
          break;
        } else if (refNode === walker.root || refNode.contains(node)) {
          break;
        }
        refNode = walker.parentNode();
      }
      if (bool) {
        return refNode;
      }
    }
    if (node.nodeType === ELEMENT_NODE) {
      let bool;
      while (refNode) {
        if (refNode === node) {
          bool = true;
          break;
        }
        refNode = walker.nextNode();
      }
      if (bool) {
        return refNode;
      }
    }
  }
  return null;
};

/**
 * Check if a node is a custom element.
 * @param {object} node - The Element node.
 * @param {object} [opt] - Options.
 * @param {boolean} [opt.formAssociated] - True if the node is form associated.
 * @returns {boolean} - True if it's a custom element.
 */
export const isCustomElement = (node, { formAssociated } = {}) => {
  if (!node?.nodeType) {
    throw new TypeError(`Unexpected type ${getType(node)}`);
  }
  if (node.nodeType !== ELEMENT_NODE) {
    return false;
  }
  const { localName, ownerDocument } = node;
  const window = ownerDocument.defaultView;
  let elmConstructor;
  const attr = node.getAttribute('is');
  if (attr) {
    elmConstructor =
      isCustomElementName(attr) && window.customElements.get(attr);
  } else {
    elmConstructor =
      isCustomElementName(localName) && window.customElements.get(localName);
  }
  if (elmConstructor) {
    if (formAssociated) {
      return !!elmConstructor.formAssociated;
    }
    return true;
  }
  return false;
};

/**
 * Get slotted text content.
 * @param {object} node - The Element node (likely a <slot>).
 * @returns {?string} - The text content.
 */
export const getSlottedTextContent = node => {
  if (!node?.nodeType) {
    throw new TypeError(`Unexpected type ${getType(node)}`);
  }
  if (typeof node.assignedNodes !== 'function') {
    return null;
  }
  const nodes = node.assignedNodes();
  if (nodes.length) {
    let text = '';
    const l = nodes.length;
    for (let i = 0; i < l; i++) {
      const item = nodes[i];
      text = item.textContent.trim();
      if (text) {
        break;
      }
    }
    return text;
  }
  return node.textContent.trim();
};

/**
 * Get directionality of a node.
 * @see https://html.spec.whatwg.org/multipage/dom.html#the-dir-attribute
 * @param {object} node - The Element node.
 * @param {WeakMap} [dirCache] - Cache for directionality.
 * @returns {?string} - 'ltr' or 'rtl'.
 */
export const getDirectionality = (node, dirCache = new WeakMap()) => {
  if (!node?.nodeType) {
    throw new TypeError(`Unexpected type ${getType(node)}`);
  }
  if (node.nodeType !== ELEMENT_NODE) {
    return null;
  }
  if (dirCache.has(node)) {
    return dirCache.get(node);
  }
  const { dir: dirAttr, localName, parentNode } = node;
  const { getEmbeddingLevels } = bidiFactory();
  let result = 'ltr';
  if (dirAttr === 'ltr' || dirAttr === 'rtl') {
    result = dirAttr;
  } else if (dirAttr === 'auto') {
    let text = '';
    switch (localName) {
      case 'input': {
        if (!node.type || KEYS_DIR_AUTO.has(node.type)) {
          text = node.value;
        } else if (KEYS_DIR_LTR.has(node.type)) {
          result = 'ltr';
          text = null; // Flag to skip text evaluation
        }
        break;
      }
      case 'slot': {
        text = getSlottedTextContent(node);
        break;
      }
      case 'textarea': {
        text = node.value;
        break;
      }
      default: {
        const items = [].slice.call(node.childNodes);
        for (const item of items) {
          const {
            dir: itemDir,
            localName: itemLocalName,
            nodeType: itemNodeType,
            textContent: itemTextContent
          } = item;
          if (itemNodeType === TEXT_NODE) {
            text = itemTextContent.trim();
          } else if (
            itemNodeType === ELEMENT_NODE &&
            !KEYS_NODE_DIR_EXCLUDE.has(itemLocalName) &&
            (!itemDir || (itemDir !== 'ltr' && itemDir !== 'rtl'))
          ) {
            if (itemLocalName === 'slot') {
              text = getSlottedTextContent(item);
            } else {
              text = itemTextContent.trim();
            }
          }
          if (text) {
            break;
          }
        }
      }
    }
    if (text !== null) {
      if (text) {
        const {
          paragraphs: [{ level }]
        } = getEmbeddingLevels(text);
        if (level % 2 === 1) {
          result = 'rtl';
        }
      } else if (parentNode) {
        const { nodeType: parentNodeType } = parentNode;
        if (parentNodeType === ELEMENT_NODE) {
          result = getDirectionality(parentNode, dirCache);
        }
      }
    }
  } else if (localName === 'input' && node.type === 'tel') {
    result = 'ltr';
  } else if (localName === 'bdi') {
    const text = node.textContent.trim();
    if (text) {
      const {
        paragraphs: [{ level }]
      } = getEmbeddingLevels(text);
      if (level % 2 === 1) {
        result = 'rtl';
      }
    }
  } else if (parentNode) {
    if (localName === 'slot') {
      const text = getSlottedTextContent(node);
      if (text) {
        const {
          paragraphs: [{ level }]
        } = getEmbeddingLevels(text);
        if (level % 2 === 1) {
          result = 'rtl';
        } else {
          result = 'ltr';
        }
      } else {
        const { nodeType: parentNodeType } = parentNode;
        if (parentNodeType === ELEMENT_NODE) {
          result = getDirectionality(parentNode, dirCache);
        }
      }
    } else {
      const { nodeType: parentNodeType } = parentNode;
      if (parentNodeType === ELEMENT_NODE) {
        result = getDirectionality(parentNode, dirCache);
      }
    }
  }
  dirCache.set(node, result);
  return result;
};

/**
 * Get language attribute of a node.
 * @param {object} node - The Element node.
 * @param {WeakMap} [langCache] - Cache for language attributes.
 * @returns {?string} - Language attribute value.
 */
export const getLanguageAttribute = (node, langCache = new WeakMap()) => {
  if (!node?.nodeType) {
    throw new TypeError(`Unexpected type ${getType(node)}`);
  }
  if (node.nodeType !== ELEMENT_NODE) {
    return null;
  }
  if (langCache.has(node)) {
    return langCache.get(node);
  }
  const { contentType } = node.ownerDocument;
  const isHtml = REG_IS_HTML.test(contentType);
  const isXml = REG_IS_XML.test(contentType);
  let isShadow = false;
  let result;
  const visited = [];
  // Traverse up from the current node to the root.
  let current = node;
  while (current) {
    if (current.nodeType === ELEMENT_NODE && langCache.has(current)) {
      result = langCache.get(current);
      break;
    }
    if (current.nodeType === ELEMENT_NODE) {
      visited.push(current);
    }
    // Check if the current node is an element.
    switch (current.nodeType) {
      case ELEMENT_NODE: {
        // Check for and return the language attribute if present.
        if (isHtml && current.hasAttribute('lang')) {
          result = current.getAttribute('lang');
        } else if (isXml && current.hasAttribute('xml:lang')) {
          result = current.getAttribute('xml:lang');
        }
        break;
      }
      case DOCUMENT_FRAGMENT_NODE: {
        // Continue traversal if the current node is a shadow root.
        if (current.host) {
          isShadow = true;
        }
        break;
      }
      case DOCUMENT_NODE:
      default: {
        // Stop if we reach the root document node.
        result = null;
      }
    }
    if (result !== undefined) {
      break;
    }
    if (isShadow) {
      current = current.host;
      isShadow = false;
    } else if (current.parentNode) {
      current = current.parentNode;
    } else {
      break;
    }
  }
  if (result === undefined) {
    result = null;
  }
  for (const visitedNode of visited) {
    langCache.set(visitedNode, result);
  }
  return result;
};

/**
 * Check if content is editable.
 * NOTE: Not implemented in jsdom https://github.com/jsdom/jsdom/issues/1670
 * @param {object} node - The Element node.
 * @returns {boolean} - True if content is editable.
 */
export const isContentEditable = node => {
  if (!node?.nodeType) {
    throw new TypeError(`Unexpected type ${getType(node)}`);
  }
  if (node.nodeType !== ELEMENT_NODE) {
    return false;
  }
  if (typeof node.isContentEditable === 'boolean') {
    return node.isContentEditable;
  } else if (node.ownerDocument.designMode === 'on') {
    return true;
  } else {
    let attr;
    if (node.hasAttribute('contenteditable')) {
      attr = node.getAttribute('contenteditable');
    } else {
      attr = 'inherit';
    }
    switch (attr) {
      case '':
      case 'true': {
        return true;
      }
      case 'plaintext-only': {
        // FIXME:
        // @see https://github.com/w3c/editing/issues/470
        // @see https://github.com/whatwg/html/issues/10651
        return true;
      }
      case 'false': {
        return false;
      }
      default: {
        if (node?.parentNode?.nodeType === ELEMENT_NODE) {
          return isContentEditable(node.parentNode);
        }
        return false;
      }
    }
  }
};

/**
 * Check if a node is visible.
 * @param {object} node - The Element node.
 * @returns {boolean} - True if the node is visible.
 */
export const isVisible = node => {
  if (node?.nodeType !== ELEMENT_NODE) {
    return false;
  }
  // TODO: switch to node.checkVisibility().
  const window = node.ownerDocument.defaultView;
  const { display, visibility } = window.getComputedStyle(node);
  return display !== 'none' && visibility === 'visible';
};

/**
 * Check if focus is visible on the node.
 * @param {object} node - The Element node.
 * @returns {boolean} - True if focus is visible.
 */
export const isFocusVisible = node => {
  if (node?.nodeType !== ELEMENT_NODE) {
    return false;
  }
  const { localName, type } = node;
  switch (localName) {
    case 'input': {
      if (!type || KEYS_INPUT_EDIT.has(type)) {
        return true;
      }
      return false;
    }
    case 'textarea': {
      return true;
    }
    default: {
      return isContentEditable(node);
    }
  }
};

/**
 * Check if an area is focusable.
 * @param {object} node - The Element node.
 * @returns {boolean} - True if the area is focusable.
 */
export const isFocusableArea = node => {
  if (node?.nodeType !== ELEMENT_NODE) {
    return false;
  }
  if (!node.isConnected) {
    return false;
  }
  const window = node.ownerDocument.defaultView;
  if (node instanceof window.HTMLElement) {
    if (Number.isInteger(parseInt(node.getAttribute('tabindex')))) {
      return true;
    }
    if (isContentEditable(node)) {
      return true;
    }
    const { localName, parentNode } = node;
    switch (localName) {
      case 'a': {
        if (node.href || node.hasAttribute('href')) {
          return true;
        }
        return false;
      }
      case 'iframe': {
        return true;
      }
      case 'input': {
        if (
          node.disabled ||
          node.hasAttribute('disabled') ||
          node.hidden ||
          node.hasAttribute('hidden')
        ) {
          return false;
        }
        return true;
      }
      case 'summary': {
        if (parentNode.localName === 'details') {
          let child = parentNode.firstElementChild;
          let bool = false;
          while (child) {
            if (child.localName === 'summary') {
              bool = child === node;
              break;
            }
            child = child.nextElementSibling;
          }
          return bool;
        }
        return false;
      }
      default: {
        if (
          KEYS_NODE_FOCUSABLE.has(localName) &&
          !(node.disabled || node.hasAttribute('disabled'))
        ) {
          return true;
        }
      }
    }
  } else if (node instanceof window.SVGElement) {
    if (Number.isInteger(parseInt(node.getAttributeNS(null, 'tabindex')))) {
      const ns = 'http://www.w3.org/2000/svg';
      let bool;
      let refNode = node;
      while (refNode.namespaceURI === ns) {
        bool = KEYS_NODE_FOCUSABLE_SVG.has(refNode.localName);
        if (bool) {
          break;
        }
        if (refNode?.parentNode?.namespaceURI === ns) {
          refNode = refNode.parentNode;
        } else {
          break;
        }
      }
      if (bool) {
        return false;
      }
      return true;
    }
    if (
      node.localName === 'a' &&
      (node.href || node.hasAttributeNS(null, 'href'))
    ) {
      return true;
    }
  }
  return false;
};

/**
 * Check if a node is focusable.
 * NOTE: Not applied, needs fix in jsdom itself.
 * @see https://github.com/whatwg/html/pull/8392
 * @see https://phabricator.services.mozilla.com/D156219
 * @see https://github.com/jsdom/jsdom/issues/3029
 * @see https://github.com/jsdom/jsdom/issues/3464
 * @param {object} node - The Element node.
 * @returns {boolean} - True if the node is focusable.
 */
export const isFocusable = node => {
  if (node?.nodeType !== ELEMENT_NODE) {
    return false;
  }
  const window = node.ownerDocument.defaultView;
  let refNode = node;
  let res = true;
  while (refNode) {
    if (refNode.disabled || refNode.hasAttribute('disabled')) {
      res = false;
      break;
    }
    if (refNode.hidden || refNode.hasAttribute('hidden')) {
      res = false;
    }
    const { contentVisibility, display, visibility } =
      window.getComputedStyle(refNode);
    if (
      display === 'none' ||
      visibility !== 'visible' ||
      (contentVisibility === 'hidden' && refNode !== node)
    ) {
      res = false;
    } else {
      res = true;
    }
    if (res && refNode?.parentNode?.nodeType === ELEMENT_NODE) {
      refNode = refNode.parentNode;
    } else {
      break;
    }
  }
  return res;
};

/**
 * Get namespace URI.
 * @param {string} ns - The namespace prefix.
 * @param {object} node - The Element node.
 * @returns {?string} - The namespace URI.
 */
export const getNamespaceURI = (ns, node) => {
  if (typeof ns !== 'string') {
    throw new TypeError(`Unexpected type ${getType(ns)}`);
  } else if (!node?.nodeType) {
    throw new TypeError(`Unexpected type ${getType(node)}`);
  }
  if (!ns || node.nodeType !== ELEMENT_NODE) {
    return null;
  }
  const { attributes } = node;
  let res;
  for (const attr of attributes) {
    const { name, namespaceURI, prefix, value } = attr;
    if (name === `xmlns:${ns}`) {
      res = value;
    } else if (prefix === ns) {
      res = namespaceURI;
    }
    if (res) {
      break;
    }
  }
  return res ?? null;
};

/**
 * Check if a namespace is declared.
 * @param {string} ns - The namespace.
 * @param {object} node - The Element node.
 * @returns {boolean} - True if the namespace is declared.
 */
export const isNamespaceDeclared = (ns = '', node = {}) => {
  if (!ns || typeof ns !== 'string' || node?.nodeType !== ELEMENT_NODE) {
    return false;
  }
  if (node.lookupNamespaceURI(ns)) {
    return true;
  }
  const root = node.ownerDocument.documentElement;
  let parent = node;
  let res;
  while (parent) {
    res = getNamespaceURI(ns, parent);
    if (res || parent === root) {
      break;
    }
    parent = parent.parentNode;
  }
  return !!res;
};

/**
 * Check if nodeA precedes and/or contains nodeB.
 * @param {object} nodeA - The first Element node.
 * @param {object} nodeB - The second Element node.
 * @returns {boolean} - True if nodeA precedes nodeB.
 */
export const isPreceding = (nodeA, nodeB) => {
  if (!nodeA?.nodeType) {
    throw new TypeError(`Unexpected type ${getType(nodeA)}`);
  } else if (!nodeB?.nodeType) {
    throw new TypeError(`Unexpected type ${getType(nodeB)}`);
  }
  if (nodeA.nodeType !== ELEMENT_NODE || nodeB.nodeType !== ELEMENT_NODE) {
    return false;
  }
  const posBit = nodeB.compareDocumentPosition(nodeA);
  const res =
    posBit & DOCUMENT_POSITION_PRECEDING || posBit & DOCUMENT_POSITION_CONTAINS;
  return !!res;
};

/**
 * Comparison function for sorting nodes based on document position.
 * @param {object} a - The first node.
 * @param {object} b - The second node.
 * @returns {number} - Sort order.
 */
export const compareNodes = (a, b) => {
  if (isPreceding(b, a)) {
    return 1;
  }
  return -1;
};

/**
 * Sort a collection of nodes.
 * @param {Array.<object>|Set.<object>} nodes - Collection of nodes.
 * @returns {Array.<object>} - Collection of sorted nodes.
 */
export const sortNodes = (nodes = []) => {
  const arr = [...nodes];
  if (arr.length > 1) {
    arr.sort(compareNodes);
  }
  return arr;
};

/**
 * Traverses AST nodes to find the most optimal seed selector
 * (ID > Class > Tag).
 * @param {Array} nodes - AST nodes to traverse.
 * @param {object} [state] - The current state of the search.
 * @returns {object} The search state containing the best seed.
 */
export const findBestSeed = (nodes, state = { seed: null, priority: 0 }) => {
  for (const node of nodes) {
    if (state.priority === 3) {
      return state;
    }
    if (Array.isArray(node)) {
      findBestSeed(node, state);
    } else if (node && typeof node === 'object') {
      // ID Selector (Fastest: getElementById)
      if (node.type === ID_SELECTOR) {
        state.seed = { type: 'id', value: node.name };
        state.priority = 3;
        return state;
      } else if (node.type === CLASS_SELECTOR && state.priority < 2) {
        // Class Selector (Faster: getElementsByClassName)
        state.seed = { type: 'class', value: node.name };
        state.priority = 2;
      } else if (
        node.type === TYPE_SELECTOR &&
        state.priority < 1 &&
        node.name !== '*'
      ) {
        // Type/Tag Selector (Excludes universal '*')
        state.seed = { type: 'tag', value: node.name };
        state.priority = 1;
      }
      if (node.children) {
        findBestSeed(node.children, state);
      }
    }
  }
  return state;
};

/**
 * Traces the DOM tree upwards and sideways from a seed element,
 * populating the allowlist with safe paths for :has() evaluation.
 * @param {object} current - The starting seed element.
 * @param {WeakSet} list - The WeakSet to populate.
 * @param {Set} visitedAncestors - The Set to track visited nodes.
 * @returns {void}
 */
export const populateHasAllowlist = (current, list, visitedAncestors) => {
  list.add(current);
  while (
    current &&
    (current.nodeType === ELEMENT_NODE ||
      current.nodeType === DOCUMENT_FRAGMENT_NODE)
  ) {
    if (visitedAncestors.has(current)) {
      break;
    }
    visitedAncestors.add(current);
    let sibling = current.previousElementSibling;
    while (sibling) {
      list.add(sibling);
      sibling = sibling.previousElementSibling;
    }
    sibling = current.nextElementSibling;
    while (sibling) {
      list.add(sibling);
      sibling = sibling.nextElementSibling;
    }
    current = current.parentNode;
    if (current) {
      list.add(current);
    }
  }
};

/**
 * Collects all descendant elements of a given node using a TreeWalker.
 * @param {Document|DocumentFragment|Element} node - The node to start from.
 * @param {Document} document - The Document used to create the TreeWalker.
 * @returns {Array<Element>} An array containing all descendant elements.
 */
export const collectAllDescendants = (node, document) => {
  if (!node?.nodeType) {
    throw new TypeError(`Unexpected type ${getType(node)}`);
  }
  if (document?.nodeType !== DOCUMENT_NODE) {
    throw new TypeError(`Unexpected type ${getType(document)}`);
  }
  const walker = document.createTreeWalker(node, SHOW_ELEMENT);
  const descendants = [];
  let refNode = walker.nextNode();
  while (refNode) {
    descendants.push(refNode);
    refNode = walker.nextNode();
  }
  return descendants;
};

/**
 * Gets the traversal direction and starting twig.
 * @param {Array.<object>} branch - The selector branch.
 * @param {string} targetType - The target type.
 * @param {boolean} hasScope - True if selector includes ':scope'.
 * @param {boolean} scoped - True if traversal is scoped within target node.
 * @returns {object} Object containing dir and twig properties.
 */
export const getTraversalStrategy = (branch, targetType, hasScope, scoped) => {
  const branchLen = branch.length;
  const firstTwig = branch[0];
  if (branchLen === 1) {
    return { dir: DIR_PREV, twig: firstTwig };
  }
  const lastTwig = branch[branchLen - 1];
  const {
    leaves: [{ name: firstName, type: firstType }]
  } = firstTwig;
  const {
    leaves: [{ name: lastName, type: lastType }]
  } = lastTwig;
  const lastCombo = branch[branchLen - 2].combo?.name;
  if (
    hasScope ||
    lastType === PS_ELEMENT_SELECTOR ||
    lastType === ID_SELECTOR ||
    lastCombo === '+' ||
    lastCombo === '~'
  ) {
    return { dir: DIR_PREV, twig: lastTwig };
  } else if (firstType === ID_SELECTOR) {
    return { dir: DIR_NEXT, twig: firstTwig };
  } else if (firstName === '*' && firstType === TYPE_SELECTOR) {
    return { dir: DIR_PREV, twig: lastTwig };
  } else if (lastName === '*' && lastType === TYPE_SELECTOR) {
    return { dir: DIR_NEXT, twig: firstTwig };
  } else if (branchLen === 1 || branchLen === 2) {
    return { dir: DIR_PREV, twig: lastTwig };
  } else if (branchLen > 2 && scoped && targetType === TARGET_FIRST) {
    return { dir: DIR_PREV, twig: lastTwig };
  }
  return { dir: DIR_NEXT, twig: firstTwig };
};
