/**
 * matcher.js
 */

/* import */
import { generateCSS, parseAstName, unescapeSelector } from './parser.js';
import {
  generateException,
  getDirectionality,
  getLanguageAttribute,
  getType,
  isContentEditable,
  isNamespaceDeclared
} from './utility.js';

/* constants */
import {
  ALPHA_NUM,
  ATTR_VALUE_I,
  INPUT_EDIT,
  LANG_PART,
  NOT_SUPPORTED_ERR,
  PS_ELEMENT_SELECTOR,
  STRING,
  SYNTAX_ERR
} from './constant.js';
const KEYS_ATTR_VALUE_I = new Set(ATTR_VALUE_I);
const KEYS_INPUT_EDIT = new Set(INPUT_EDIT);

/* regexp */
const REG_LANG_VALID = new RegExp(`^(?:\\*-)?${ALPHA_NUM}${LANG_PART}$`, 'i');

/* cache */
const astMetaCache = new WeakMap();

/**
 * Validates a pseudo-element selector.
 * @param {string} astName - The name of the pseudo-element from the AST.
 * @param {string} astType - The type of the selector from the AST.
 * @param {object} [opt] - Optional parameters.
 * @param {boolean} [opt.forgive] - If true, ignores unknown pseudo-elements.
 * @param {object} [opt.globalObject] - The global object.
 * @param {boolean} [opt.warn] - If true, throws an error for unsupported ones.
 * @throws {DOMException} If the selector is invalid or unsupported.
 * @returns {void}
 */
export const matchPseudoElementSelector = (
  astName,
  astType,
  { forgive, globalObject, warn } = {}
) => {
  if (astType !== PS_ELEMENT_SELECTOR) {
    // Ensure the AST node is a pseudo-element selector.
    throw new TypeError(`Unexpected ast type ${getType(astType)}`);
  }
  switch (astName) {
    case 'after':
    case 'backdrop':
    case 'before':
    case 'cue':
    case 'cue-region':
    case 'first-letter':
    case 'first-line':
    case 'file-selector-button':
    case 'marker':
    case 'placeholder':
    case 'selection':
    case 'target-text': {
      // Warn if the pseudo-element is known but unsupported.
      if (warn) {
        throw generateException(
          `Unsupported pseudo-element ::${astName}`,
          NOT_SUPPORTED_ERR,
          globalObject
        );
      }
      break;
    }
    case 'part':
    case 'slotted': {
      // Warn if the functional pseudo-element is known but unsupported.
      if (warn) {
        throw generateException(
          `Unsupported pseudo-element ::${astName}()`,
          NOT_SUPPORTED_ERR,
          globalObject
        );
      }
      break;
    }
    default: {
      // Handle vendor-prefixed unknown pseudo-elements.
      if (astName.startsWith('-webkit-')) {
        if (warn) {
          throw generateException(
            `Unsupported pseudo-element ::${astName}`,
            NOT_SUPPORTED_ERR,
            globalObject
          );
        }
      } else if (!forgive) {
        // Throw an error for unknown pseudo-elements if not forgiven.
        throw generateException(
          `Unknown pseudo-element ::${astName}`,
          SYNTAX_ERR,
          globalObject
        );
      }
    }
  }
};

/**
 * Matches the :dir() pseudo-class against an element's directionality.
 * @param {object} ast - The AST object for the pseudo-class.
 * @param {object} node - The element node to match against.
 * @param {WeakMap} [dirCache] - Cache for directionality.
 * @throws {TypeError} If the AST does not contain a valid direction value.
 * @returns {boolean} - True if matches, otherwise false.
 */
export const matchDirectionPseudoClass = (
  ast,
  node,
  dirCache = new WeakMap()
) => {
  const { name } = ast;
  if (!name) {
    const type = name === '' ? '(empty String)' : getType(name);
    throw new TypeError(`Unexpected ast type ${type}`);
  }
  const dir = getDirectionality(node, dirCache);
  return name === dir;
};

/**
 * Matches the :lang() pseudo-class against an element's language attribute.
 * @param {object} ast - The AST object for the pseudo-class child.
 * @param {object} node - The element node to match against.
 * @param {WeakMap} [langCache] - Cache for language attributes.
 * @throws {TypeError} If the AST does not contain a valid language value.
 * @returns {boolean} - True if matches, otherwise false.
 */
export const matchLanguagePseudoClass = (
  ast,
  node,
  langCache = new WeakMap()
) => {
  const elementLang = getLanguageAttribute(node, langCache);
  if (elementLang === null) {
    return false;
  }
  let meta = astMetaCache.get(ast);
  if (meta === undefined) {
    meta = {};
    astMetaCache.set(ast, meta);
  }
  if (meta.langRegex !== undefined) {
    if (meta.langPattern === '*') {
      return elementLang !== '';
    }
    if (meta.langRegex === null) {
      return false;
    }
    return meta.langRegex.test(elementLang);
  }
  const { name, type, value } = ast;
  const langPattern =
    type === STRING && value !== undefined ? value : unescapeSelector(name);
  meta.langPattern = langPattern;
  if (typeof langPattern !== 'string') {
    meta.langRegex = null;
    return false;
  }
  if (langPattern === '*') {
    meta.langRegex = null;
    return elementLang !== '';
  }
  if (!REG_LANG_VALID.test(langPattern)) {
    meta.langRegex = null;
    return false;
  }
  const regexStr = langPattern
    .split('-')
    .map((part, index) => {
      const core = part === '*' ? ALPHA_NUM : part;
      return (index === 0 ? core : `-${core}`) + LANG_PART;
    })
    .join('');
  const matcherRegex = new RegExp(`^${regexStr}$`, 'i');
  meta.langRegex = matcherRegex;
  return matcherRegex.test(elementLang);
};

/**
 * Matches the :checked pseudo-class.
 * @param {object} node - The Element node.
 * @returns {boolean} True if matches, otherwise false.
 */
export const matchCheckedPseudoClass = node => {
  const { localName } = node;
  if (localName === 'option') {
    return node.selected;
  }
  if (localName === 'input') {
    const attrType = node.getAttribute('type');
    if (node.checked) {
      return attrType === 'checkbox' || attrType === 'radio';
    }
  }
  return false;
};

/**
 * Matches the :any-link and :link pseudo-classes.
 * @param {object} node - The Element node.
 * @returns {boolean} True if matches, otherwise false.
 */
export const matchLinkPseudoClass = node => {
  const { localName } = node;
  if (localName === 'a' || localName === 'area') {
    return node.hasAttribute('href');
  }
  return false;
};

/**
 * Matches the :open pseudo-class.
 * @param {object} node - The Element node.
 * @returns {boolean} True if matches, otherwise false.
 */
export const matchOpenPseudoClass = node => {
  const { localName } = node;
  if (localName === 'details' || localName === 'dialog') {
    return node.hasAttribute('open');
  }
  return false;
};

/**
 * Matches the :placeholder-shown pseudo-class.
 * @param {object} node - The Element node.
 * @param {Set.<string>} keys - A set of input type keys.
 * @returns {boolean} True if matches, otherwise false.
 */
export const matchPlaceholderShownPseudoClass = (node, keys) => {
  let placeholder;
  if (node.placeholder) {
    placeholder = node.placeholder;
  } else if (node.hasAttribute('placeholder')) {
    placeholder = node.getAttribute('placeholder');
  }
  if (typeof placeholder === 'string' && !/[\r\n]/.test(placeholder)) {
    let targetNode;
    const { localName } = node;
    if (localName === 'textarea') {
      targetNode = node;
    } else if (localName === 'input') {
      if (node.hasAttribute('type')) {
        if (keys.has(node.getAttribute('type'))) {
          targetNode = node;
        }
      } else {
        targetNode = node;
      }
    }
    if (targetNode) {
      return node.value === '';
    }
  }
  return false;
};

/**
 * Matches the :in-range and :out-of-range pseudo-classes.
 * @param {string} astName - The name of the pseudo-class.
 * @param {object} node - The Element node.
 * @param {Set.<string>} keys - A set of input type keys.
 * @returns {boolean} True if matches, otherwise false.
 */
export const matchRangePseudoClass = (astName, node, keys) => {
  const { localName } = node;
  const attrType = node.getAttribute('type');
  if (
    localName === 'input' &&
    !(node.readOnly || node.hasAttribute('readonly')) &&
    !(node.disabled || node.hasAttribute('disabled')) &&
    keys.has(attrType)
  ) {
    const flowed = node.validity.rangeUnderflow || node.validity.rangeOverflow;
    if (astName === 'out-of-range') {
      return flowed;
    }
    if (flowed) {
      return false;
    }
    return (
      node.hasAttribute('min') ||
      node.hasAttribute('max') ||
      attrType === 'range'
    );
  }
  return false;
};

/**
 * Match the :read-only and :read-write pseudo-classes
 * @param {string} astName - pseudo-class name
 * @param {object} node - Element node
 * @returns {boolean} - True if matches, otherwise false.
 */
export const matchReadOnlyPseudoClass = (astName, node) => {
  const { localName } = node;
  let isReadOnly = false;
  switch (localName) {
    case 'textarea':
    case 'input': {
      const isEditableInput = !node.type || KEYS_INPUT_EDIT.has(node.type);
      if (localName === 'textarea' || isEditableInput) {
        isReadOnly =
          node.readOnly ||
          node.hasAttribute('readonly') ||
          node.disabled ||
          node.hasAttribute('disabled');
      } else {
        // Non-editable input types are always read-only
        isReadOnly = true;
      }
      break;
    }
    default: {
      isReadOnly = !isContentEditable(node);
    }
  }
  if (astName === 'read-only') {
    return isReadOnly;
  }
  return !isReadOnly;
};

/**
 * Matches the :required and :optional pseudo-classes.
 * @param {string} astName - The name of the pseudo-class.
 * @param {object} node - The Element node.
 * @param {Set.<string>} keys - A set of input type keys.
 * @returns {boolean} True if matches, otherwise false.
 */
export const matchRequiredPseudoClass = (astName, node, keys) => {
  const { localName } = node;
  let required = false;
  if (localName === 'select' || localName === 'textarea') {
    if (node.required || node.hasAttribute('required')) {
      required = true;
    }
  } else if (localName === 'input') {
    if (node.hasAttribute('type')) {
      const attrType = node.getAttribute('type');
      if (keys.has(attrType)) {
        if (node.required || node.hasAttribute('required')) {
          required = true;
        }
      }
    } else if (node.required || node.hasAttribute('required')) {
      required = true;
    }
  } else {
    return false;
  }
  if (astName === 'optional') {
    return !required;
  }
  return required;
};

/**
 * Matches an attribute selector against an element.
 * @param {object} ast - The AST for the attribute selector.
 * @param {object} node - The element node to match against.
 * @param {object} [opt] - Optional parameters.
 * @param {boolean} [opt.check] - True if running in an internal check.
 * @param {boolean} [opt.forgive] - True to forgive certain syntax errors.
 * @param {object} [opt.globalObject] - The global object.
 * @returns {boolean} - True if the attribute selector matches, otherwise false.
 */
export const matchAttributeSelector = (
  ast,
  node,
  { check, forgive, globalObject } = {}
) => {
  const {
    flags: astFlags,
    matcher: astMatcher,
    name: astName,
    value: astValue
  } = ast;
  if (typeof astFlags === 'string' && !/^[is]$/i.test(astFlags) && !forgive) {
    const css = generateCSS(ast);
    throw generateException(
      `Invalid selector ${css}`,
      SYNTAX_ERR,
      globalObject
    );
  }
  const isHTML = node.ownerDocument.contentType === 'text/html';
  let meta = astMetaCache.get(ast);
  if (meta === undefined) {
    meta = {
      attrValues: new Set()
    };
    astMetaCache.set(ast, meta);
  }
  if (astMatcher === null && !astFlags && typeof astName?.name === 'string') {
    if (meta.astName === undefined) {
      const rawName = unescapeSelector(astName.name);
      meta.astName = rawName;
      meta.hasPipe = rawName.indexOf('|') > -1;
    }
    if (!meta.hasPipe) {
      if (
        meta.astName === 'lang' &&
        node.hasAttributeNS('http://www.w3.org/XML/1998/namespace', 'lang')
      ) {
        return false;
      }
      if (node.hasAttribute(meta.astName)) {
        return true;
      }
      const attrs = node.attributes;
      if (!attrs || attrs.length === 0) {
        return false;
      }
      const checkName = isHTML ? meta.astName.toLowerCase() : meta.astName;
      for (let i = 0, len = attrs.length; i < len; i++) {
        let itemName = attrs[i].name;
        if (isHTML) {
          itemName = itemName.toLowerCase();
        }
        const colonIdx = itemName.indexOf(':');
        if (colonIdx > -1) {
          const itemLocalName = itemName
            .substring(colonIdx + 1)
            .replace(/^:/, '');
          if (checkName === itemLocalName) {
            return true;
          }
        } else if (checkName === itemName) {
          return true;
        }
      }
      return false;
    }
  }
  const { attributes } = node;
  if (!attributes || !attributes.length) {
    return false;
  }
  if (meta.caseInsensitive === undefined) {
    let caseInsensitive = false;
    if (typeof astFlags === 'string') {
      caseInsensitive = /^i$/i.test(astFlags);
    } else if (isHTML) {
      caseInsensitive = KEYS_ATTR_VALUE_I.has(astName.name);
    }
    meta.caseInsensitive = caseInsensitive;
    let astAttrName = unescapeSelector(astName.name);
    meta.hasPipeInName = astAttrName.indexOf('|') > -1;
    if ((isHTML && !meta.hasPipeInName) || caseInsensitive) {
      astAttrName = astAttrName.toLowerCase();
    }
    meta.astAttrName = astAttrName;
    if (meta.hasPipeInName) {
      const { prefix, localName } = parseAstName(astAttrName);
      meta.astPrefix = prefix;
      meta.astLocalName = localName;
    }
    const { name: astIdentValue, value: astStringValue } = astValue ?? {};
    let attrValue;
    if (astIdentValue) {
      attrValue = unescapeSelector(astIdentValue);
    } else if (astStringValue !== undefined) {
      attrValue = astStringValue;
    }
    if (caseInsensitive && typeof attrValue === 'string') {
      attrValue = attrValue.toLowerCase();
    }
    meta.cachedAttrValue = attrValue;
    if (astMatcher === '~=' && attrValue && typeof attrValue === 'string') {
      meta.tildeTarget = /\s/.test(attrValue) ? null : ` ${attrValue} `;
    }
  }
  const caseInsensitive = meta.caseInsensitive;
  const astAttrName = meta.astAttrName;
  const attrValue = meta.cachedAttrValue;
  const attrValues = meta.attrValues;
  if (attrValues.size) {
    attrValues.clear();
  }
  if (meta.hasPipeInName) {
    const astPrefix = meta.astPrefix;
    const astLocalName = meta.astLocalName;
    for (let i = 0, len = attributes.length; i < len; i++) {
      const item = attributes[i];
      let itemName = item.name;
      let itemValue = item.value;
      if (caseInsensitive) {
        itemName = itemName.toLowerCase();
        itemValue = itemValue.toLowerCase();
      }
      const colonIdx = itemName.indexOf(':');
      switch (astPrefix) {
        case '': {
          if (astLocalName === itemName) {
            attrValues.add(itemValue);
          }
          break;
        }
        case '*': {
          if (colonIdx > -1) {
            const itemLocalName = itemName
              .substring(colonIdx + 1)
              .replace(/^:/, '');
            if (itemLocalName === astLocalName) {
              attrValues.add(itemValue);
            }
          } else if (astLocalName === itemName) {
            attrValues.add(itemValue);
          }
          break;
        }
        default: {
          if (!check) {
            if (forgive) {
              return false;
            }
            const css = generateCSS(ast);
            throw generateException(
              `Invalid selector ${css}`,
              SYNTAX_ERR,
              globalObject
            );
          }
          if (colonIdx > -1) {
            const itemPrefix = itemName.substring(0, colonIdx);
            const itemLocalName = itemName
              .substring(colonIdx + 1)
              .replace(/^:/, '');
            if (itemPrefix === 'xml' && itemLocalName === 'lang') {
              continue;
            }
            if (astPrefix === itemPrefix && astLocalName === itemLocalName) {
              if (isNamespaceDeclared(astPrefix, node)) {
                attrValues.add(itemValue);
              }
            }
          }
        }
      }
    }
  } else {
    for (let i = 0, len = attributes.length; i < len; i++) {
      const item = attributes[i];
      const origName = item.name;
      if (
        item.namespaceURI === 'http://www.w3.org/XML/1998/namespace' &&
        item.localName === 'lang'
      ) {
        continue;
      }
      const colonIdx = origName.indexOf(':');
      if (colonIdx > -1) {
        const itemPrefix = origName.substring(0, colonIdx);
        const itemLocalName = origName
          .substring(colonIdx + 1)
          .replace(/^:/, '');
        if (itemPrefix === 'xml' && itemLocalName === 'lang') {
          continue;
        }
      }
      let isMatch = false;
      if (origName === astAttrName) {
        isMatch = true;
      } else if (caseInsensitive && origName.toLowerCase() === astAttrName) {
        isMatch = true;
      }
      if (isMatch) {
        attrValues.add(caseInsensitive ? item.value.toLowerCase() : item.value);
      } else if (colonIdx > -1) {
        const itemLocalName = origName
          .substring(colonIdx + 1)
          .replace(/^:/, '');
        let isLocalMatch = false;
        if (itemLocalName === astAttrName) {
          isLocalMatch = true;
        } else if (
          caseInsensitive &&
          itemLocalName.toLowerCase() === astAttrName
        ) {
          isLocalMatch = true;
        }
        if (isLocalMatch) {
          attrValues.add(
            caseInsensitive ? item.value.toLowerCase() : item.value
          );
        }
      }
    }
  }
  if (!attrValues.size) {
    return false;
  }
  switch (astMatcher) {
    case '=': {
      return typeof attrValue === 'string' && attrValues.has(attrValue);
    }
    case '~=': {
      if (meta.tildeTarget === null || !attrValue) {
        return false;
      }
      const target = meta.tildeTarget;
      for (const value of attrValues) {
        if (` ${value.replace(/[\t\r\n\f]/g, ' ')} `.includes(target)) {
          return true;
        }
      }
      return false;
    }
    case '|=': {
      if (!attrValue || typeof attrValue !== 'string') {
        return false;
      }
      const prefix = `${attrValue}-`;
      for (const value of attrValues) {
        if (value === attrValue || value.startsWith(prefix)) {
          return true;
        }
      }
      return false;
    }
    case '^=': {
      if (!attrValue || typeof attrValue !== 'string') {
        return false;
      }
      for (const value of attrValues) {
        if (value.startsWith(attrValue)) {
          return true;
        }
      }
      return false;
    }
    case '$=': {
      if (!attrValue || typeof attrValue !== 'string') {
        return false;
      }
      for (const value of attrValues) {
        if (value.endsWith(attrValue)) {
          return true;
        }
      }
      return false;
    }
    case '*=': {
      if (!attrValue || typeof attrValue !== 'string') {
        return false;
      }
      for (const value of attrValues) {
        if (value.includes(attrValue)) {
          return true;
        }
      }
      return false;
    }
    case null:
    default: {
      return true;
    }
  }
};

/**
 * Matches a type selector against an element.
 * @param {object} ast - The AST for the type selector.
 * @param {object} node - The element node to match against.
 * @param {object} [opt] - Optional parameters.
 * @param {boolean} [opt.check] - True if running in an internal check.
 * @param {boolean} [opt.forgive] - True to forgive undeclared namespace.
 * @param {object} [opt.globalObject] - The global object.
 * @returns {boolean} - True if the type selector matches, otherwise false.
 */
export const matchTypeSelector = (
  ast,
  node,
  { check, forgive, globalObject } = {}
) => {
  const { localName, namespaceURI, prefix } = node;
  let meta = astMetaCache.get(ast);
  if (meta === undefined) {
    meta = {};
    astMetaCache.set(ast, meta);
  }
  if (meta.astName === undefined) {
    const astName = unescapeSelector(ast.name);
    const { prefix: parsedPrefix, localName: parsedLocalName } = parseAstName(
      astName,
      node
    );
    meta.astName = astName;
    meta.astPrefix = parsedPrefix;
    meta.astPrefixLowerCased = parsedPrefix.toLowerCase();
    meta.astLocalName = parsedLocalName;
    meta.astLocalNameLowerCased = parsedLocalName.toLowerCase();
    meta.hasPipe = astName.includes('|');
  }
  const isHTML =
    node.ownerDocument.contentType === 'text/html' &&
    (!namespaceURI || namespaceURI === 'http://www.w3.org/1999/xhtml');
  if (isHTML && localName === meta.astLocalName && !meta.hasPipe) {
    return true;
  }
  let nodePrefix;
  let nodeLocalName;
  const colonIdx = localName.indexOf(':');
  if (colonIdx > -1) {
    nodePrefix = localName.substring(0, colonIdx);
    nodeLocalName = localName.substring(colonIdx + 1);
  } else {
    nodePrefix = prefix || '';
    nodeLocalName = localName;
  }
  const astPrefix = isHTML ? meta.astPrefixLowerCased : meta.astPrefix;
  const astLocalName = isHTML ? meta.astLocalNameLowerCased : meta.astLocalName;
  const isUniversal = astLocalName === '*';
  switch (astPrefix) {
    case '': {
      return (
        !nodePrefix &&
        !namespaceURI &&
        (isUniversal || astLocalName === nodeLocalName)
      );
    }
    case '*': {
      return isUniversal || astLocalName === nodeLocalName;
    }
    default: {
      if (!check) {
        if (forgive) {
          return false;
        }
        const css = generateCSS(ast);
        throw generateException(
          `Invalid selector ${css}`,
          SYNTAX_ERR,
          globalObject
        );
      }
      const astNS = node.lookupNamespaceURI(astPrefix);
      const nodeNS = node.lookupNamespaceURI(nodePrefix);
      if (astNS === nodeNS && astPrefix === nodePrefix) {
        return isUniversal || astLocalName === nodeLocalName;
      } else if (!forgive && !astNS) {
        throw generateException(
          `Undeclared namespace ${astPrefix}`,
          SYNTAX_ERR,
          globalObject
        );
      }
      return false;
    }
  }
};
