/**
 * finder.js
 */

/* import */
import { Evaluator } from './evaluator.js';
import { Mapper } from './mapper.js';
import { matchPseudoElementSelector } from './matcher.js';
import { generateCSS, unescapeSelector } from './parser.js';
import { getTraversalStrategy, sortNodes, traverseNode } from './utility.js';

/* constants */
import {
  CLASS_SELECTOR,
  DIR_NEXT,
  DIR_PREV,
  DOCUMENT_FRAGMENT_NODE,
  ELEMENT_NODE,
  ID_SELECTOR,
  PS_ELEMENT_SELECTOR,
  TARGET_ALL,
  TARGET_FIRST,
  TARGET_LINEAL,
  TARGET_SELF,
  TYPE_SELECTOR
} from './constant.js';

/**
 * Finder
 * Evaluates CSS selectors to find and collect matched nodes.
 * NOTE: #ast[i] corresponds to #nodes[i]
 */
export class Finder extends Evaluator {
  /* private fields */
  #ast;
  #mapper;
  #nodeWalker;
  #nodes;
  #rootWalker;
  #scoped;
  #selector;
  #selectorAST;

  /**
   * Sets up the finder.
   * @param {string} selector - The CSS selector.
   * @param {object} node - Document, DocumentFragment, or Element.
   * @param {object} [opt] - Options.
   * @param {boolean} [opt.check] - True if running in internal check.
   * @param {boolean} [opt.noexcept] - True to suppress exceptions.
   * @param {boolean} [opt.warn] - True to enable console warnings.
   * @returns {object} The Finder instance.
   */
  setup(selector, node, opt = {}) {
    super.setup(selector, node, opt);
    this.#ast = null;
    this.#mapper = new Mapper(this);
    this.#nodeWalker = null;
    this.#nodes = null;
    this.#scoped =
      this.node !== this.root && this.node.nodeType === ELEMENT_NODE;
    this.#rootWalker = null;
    this.#selector = selector;
    this.#selectorAST = null;
    return this;
  }

  /**
   * Finds matched nodes.
   * @param {string} targetType - The target type.
   * @returns {Set.<object>|object} A collection of matched nodes.
   */
  find = targetType => {
    let collection;
    try {
      collection = this.#collectNodes(targetType);
    } catch (e) {
      if (this.check) {
        return {
          ast: this.#selectorAST,
          match: false,
          pseudoElement: this.pseudoElements.length
            ? this.pseudoElements.join('')
            : null
        };
      } else {
        throw e;
      }
    }
    const [[...branches], collectedNodes] = collection;
    const l = branches.length;
    let sort = l > 1 && targetType === TARGET_ALL;
    let nodes = new Set();
    for (let i = 0; i < l; i++) {
      const { branch, dir, find } = branches[i];
      if (!branch.length || !find) {
        continue;
      }
      const entryNodes = collectedNodes[i];
      const lastIndex = branch.length - 1;
      if (lastIndex === 0) {
        if (
          (targetType === TARGET_ALL || targetType === TARGET_FIRST) &&
          this.node.nodeType === ELEMENT_NODE
        ) {
          for (const node of entryNodes) {
            if (node !== this.node) {
              if (targetType === TARGET_ALL || this.node.contains(node)) {
                nodes.add(node);
                if (targetType === TARGET_FIRST) {
                  break;
                }
              }
            }
          }
        } else if (targetType === TARGET_ALL) {
          if (nodes.size) {
            for (const node of entryNodes) {
              nodes.add(node);
            }
            sort = true;
          } else {
            nodes = new Set(entryNodes);
          }
        } else {
          if (entryNodes.length) {
            nodes.add(entryNodes[0]);
          }
        }
      } else if (targetType === TARGET_ALL) {
        const newNodes = this.#processComplexBranchAll(branch, entryNodes, dir);
        if (nodes.size) {
          for (const newNode of newNodes) {
            nodes.add(newNode);
          }
          sort = true;
        } else {
          nodes = newNodes;
        }
      } else {
        const matchedNode = this.#processComplexBranchFirst(
          branch,
          entryNodes,
          dir,
          targetType
        );
        if (matchedNode) {
          nodes.add(matchedNode);
        }
      }
    }
    if (this.check) {
      return {
        ast: this.#selectorAST,
        match: nodes.size > 0,
        pseudoElement: this.pseudoElements.length
          ? this.pseudoElements.join('')
          : null
      };
    }
    if (targetType === TARGET_FIRST || targetType === TARGET_ALL) {
      nodes.delete(this.node);
    }
    if ((sort || targetType === TARGET_FIRST) && nodes.size > 1) {
      return new Set(sortNodes(nodes));
    }
    return nodes;
  };

  /**
   * Traverses and collects nodes matching leaves.
   * @private
   * @param {object} walker - The TreeWalker instance.
   * @param {Array.<object>} leaves - The AST leaves to match.
   * @param {object} [opt] - Options for traversal.
   * @returns {Array.<object>} An array of collected nodes.
   */
  #traverseAndCollectNodes = (walker, leaves, opt = {}) => {
    const { boundaryNode, force, startNode, targetType } = opt;
    const collectedNodes = [];
    let currentNode = traverseNode(startNode, walker, !!force);
    if (currentNode.nodeType !== ELEMENT_NODE) {
      currentNode = walker.nextNode();
    } else if (currentNode === startNode && currentNode !== this.root) {
      currentNode = walker.nextNode();
    }
    while (currentNode) {
      if (boundaryNode) {
        if (currentNode === boundaryNode) {
          break;
        } else if (
          targetType === TARGET_ALL &&
          !boundaryNode.contains(currentNode)
        ) {
          break;
        }
      }
      if (
        this.matchLeaves(leaves, currentNode, this.matchOpts) &&
        currentNode !== this.node
      ) {
        collectedNodes.push(currentNode);
        if (targetType !== TARGET_ALL) {
          break;
        }
      }
      currentNode = walker.nextNode();
    }
    return collectedNodes;
  };

  /**
   * Finds matching nodes preceding the current node.
   * @private
   * @param {Array.<object>} leaves - The AST leaves to match.
   * @param {object} node - The starting node.
   * @param {object} [opt] - Options for finding.
   * @returns {Array.<object>} An array of matched nodes.
   */
  #findPrecede = (leaves, node, opt = {}) => {
    const { force, targetType } = opt;
    if (!this.#rootWalker) {
      this.#rootWalker = this.createTreeWalker(this.root);
    }
    return this.#traverseAndCollectNodes(this.#rootWalker, leaves, {
      force,
      targetType,
      boundaryNode: this.node,
      startNode: node
    });
  };

  /**
   * Finds matching nodes using TreeWalker.
   * @private
   * @param {Array.<object>} leaves - The AST leaves.
   * @param {object} node - The starting node.
   * @param {object} [opt] - Traversal options.
   * @returns {Array.<object>} An array of matched nodes.
   */
  #findNodeWalker = (leaves, node, opt = {}) => {
    const { precede, ...traversalOpts } = opt;
    if (precede) {
      const precedeNodes = this.#findPrecede(leaves, this.root, opt);
      if (precedeNodes.length) {
        return precedeNodes;
      }
    }
    if (!this.#nodeWalker) {
      this.#nodeWalker = this.createTreeWalker(this.node);
    }
    return this.#traverseAndCollectNodes(this.#nodeWalker, leaves, {
      ...traversalOpts,
      startNode: node
    });
  };

  /**
   * Matches the current node itself against leaves.
   * @private
   * @param {Array.<object>} leaves - The AST leaves.
   * @returns {Array} Array with nodes, match boolean, and pseudo-elements.
   */
  #matchSelf = leaves => {
    const matched = this.matchLeaves(leaves, this.node, {
      check: this.check,
      warn: this.warn
    });
    const nodes = matched ? [this.node] : [];
    return [nodes, matched, this.pseudoElements];
  };

  /**
   * Finds lineal matching nodes (self and ancestors).
   * @private
   * @param {Array.<object>} leaves - The AST leaves.
   * @param {object} [opt] - Options like complex flag.
   * @returns {Array} Array containing nodes and filtered boolean.
   */
  #findLineal = (leaves, opt = {}) => {
    const { complex } = opt;
    const nodes = [];
    const selfMatched = this.matchLeaves(leaves, this.node, this.matchOpts);
    if (selfMatched) {
      nodes.push(this.node);
    }
    if (!selfMatched || complex) {
      let currentNode = this.node.parentNode;
      while (currentNode) {
        if (this.matchLeaves(leaves, currentNode, this.matchOpts)) {
          nodes.push(currentNode);
        }
        currentNode = currentNode.parentNode;
      }
    }
    const filtered = nodes.length > 0;
    return [nodes, filtered];
  };

  /**
   * Performs early evaluation for TARGET_SELF and TARGET_LINEAL.
   * @private
   * @param {Array.<object>} leaves - The AST leaves.
   * @param {string} targetType - The target type.
   * @param {boolean} complex - Indicates if the branch is complex.
   * @param {boolean} compound - Indicates if there are filter leaves.
   * @returns {object|null} The result object if matched, or null otherwise.
   */
  #checkSelfOrLinealTarget = (leaves, targetType, complex, compound) => {
    if (targetType === TARGET_SELF) {
      const [nodes, filtered] = this.#matchSelf(leaves);
      return { compound, filtered, nodes, pending: false };
    } else if (targetType === TARGET_LINEAL) {
      const [nodes, filtered] = this.#findLineal(leaves, { complex });
      return { compound, filtered, nodes, pending: false };
    }
    return null;
  };

  /**
   * Standardizes the loop processing and filtering of a collection.
   * @private
   * @param {object} collection - The HTMLCollection or NodeList to process.
   * @param {Array.<object>} filterLeaves - Leaves for filtering.
   * @param {boolean} compound - Indicates if there are filter leaves.
   * @returns {object} Result object with nodes and flags.
   */
  #filterAndFormatCollection = (collection, filterLeaves, compound) => {
    const len = collection.length;
    const hasFilter = filterLeaves.length > 0;
    const nodeArray = [];
    for (let i = 0; i < len; i++) {
      const currentNode = collection[i];
      if (
        !hasFilter ||
        this.matchLeaves(filterLeaves, currentNode, this.matchOpts)
      ) {
        nodeArray.push(currentNode);
      }
    }
    return {
      compound,
      filtered: nodeArray.length > 0,
      nodes: nodeArray,
      pending: false
    };
  };

  /**
   * Returns the fallback search result using NodeWalker.
   * @private
   * @param {Array.<object>} leaves - The AST leaves.
   * @param {string} targetType - The target type.
   * @param {boolean} precede - Indicates if searching preceding nodes.
   * @param {boolean} compound - Indicates if there are filter leaves.
   * @returns {object} Result object with nodes and flags.
   */
  #fallbackToWalkerResult = (leaves, targetType, precede, compound) => {
    const nodes = this.#findNodeWalker(leaves, this.node, {
      precede,
      targetType
    });
    return { compound, filtered: nodes.length > 0, nodes, pending: false };
  };

  /**
   * Finds entry nodes for pseudo-elements.
   * @private
   * @param {object} leaf - The AST leaf.
   * @param {Array.<object>} filterLeaves - Leaves for filtering.
   * @param {string} targetType - The target type.
   * @returns {object} Object with nodes, filtered, and pending flags.
   */
  #findEntryNodesForPseudoElement = (leaf, filterLeaves, targetType) => {
    const compound = filterLeaves.length > 0;
    if (targetType === TARGET_SELF && this.check) {
      const css = generateCSS(leaf);
      this.pseudoElements.push(css);
      if (filterLeaves.length) {
        const [nodes, filtered] = this.#matchSelf(filterLeaves);
        return { compound, filtered, nodes, pending: false };
      }
      return { compound, filtered: true, nodes: [this.node], pending: false };
    }
    matchPseudoElementSelector(leaf.name, leaf.type, this.matchOpts);
    return { compound, filtered: false, nodes: [], pending: false };
  };

  /**
   * Finds entry nodes using ID selector strategy.
   * @private
   * @param {object} twig - The twig object containing leaves.
   * @param {string} targetType - The target type.
   * @param {object} [opt] - Strategy options.
   * @returns {object} Result object with nodes and flags.
   */
  #findEntryNodesForId = (twig, targetType, opt = {}) => {
    const { leaves } = twig;
    const { complex, precede, filterLeaves = [] } = opt;
    const compound = filterLeaves.length > 0;
    const earlyResult = this.#checkSelfOrLinealTarget(
      leaves,
      targetType,
      complex,
      compound
    );
    if (earlyResult) {
      return earlyResult;
    }
    if (
      targetType === TARGET_FIRST &&
      this.root.nodeType !== ELEMENT_NODE &&
      this.node.nodeType !== ELEMENT_NODE
    ) {
      const [leaf] = leaves;
      const node = this.root.getElementById(leaf.name);
      const nodes = [];
      if (node) {
        if (filterLeaves.length) {
          if (this.matchLeaves(filterLeaves, node, this.matchOpts)) {
            nodes.push(node);
          }
        } else {
          nodes.push(node);
        }
      }
      return { compound, filtered: nodes.length > 0, nodes, pending: false };
    }
    return this.#fallbackToWalkerResult(leaves, targetType, precede, compound);
  };

  /**
   * Finds entry nodes using class selector strategy.
   * @private
   * @param {Array.<object>} leaves - The AST leaves.
   * @param {string} targetType - The target type.
   * @param {object} [opt] - Strategy options.
   * @returns {object} Result object with nodes and flags.
   */
  #findEntryNodesForClass = (leaves, targetType, opt = {}) => {
    const { complex, precede, filterLeaves = [] } = opt;
    const compound = filterLeaves.length > 0;
    const earlyResult = this.#checkSelfOrLinealTarget(
      leaves,
      targetType,
      complex,
      compound
    );
    if (earlyResult) {
      return earlyResult;
    }
    if (
      targetType !== TARGET_FIRST &&
      !precede &&
      typeof this.node.getElementsByClassName === 'function'
    ) {
      this.matchLeaves(leaves, this.node, this.matchOpts);
      const [leaf] = leaves;
      const className = unescapeSelector(leaf.name);
      const collection = this.node.getElementsByClassName(className);
      return this.#filterAndFormatCollection(
        collection,
        filterLeaves,
        compound
      );
    }
    return this.#fallbackToWalkerResult(leaves, targetType, precede, compound);
  };

  /**
   * Finds entry nodes using type selector strategy.
   * @private
   * @param {Array.<object>} leaves - The AST leaves.
   * @param {string} targetType - The target type.
   * @param {object} [opt] - Strategy options.
   * @returns {object} Result object with nodes and flags.
   */
  #findEntryNodesForType = (leaves, targetType, opt = {}) => {
    const { complex, precede, filterLeaves = [] } = opt;
    const compound = filterLeaves.length > 0;
    const earlyResult = this.#checkSelfOrLinealTarget(
      leaves,
      targetType,
      complex,
      compound
    );
    if (earlyResult) {
      return earlyResult;
    }
    const [leaf] = leaves;
    const tagName = unescapeSelector(leaf.name);
    if (
      targetType !== TARGET_FIRST &&
      !precede &&
      this.document.contentType === 'text/html' &&
      typeof this.node.getElementsByTagName === 'function' &&
      tagName.indexOf('|') === -1
    ) {
      this.matchLeaves(leaves, this.node, this.matchOpts);
      const collection = this.node.getElementsByTagName(tagName);
      return this.#filterAndFormatCollection(
        collection,
        filterLeaves,
        compound
      );
    }
    return this.#fallbackToWalkerResult(leaves, targetType, precede, compound);
  };

  /**
   * Finds entry nodes for other selector types.
   * @private
   * @param {object} twig - The twig object containing leaves.
   * @param {string} targetType - The target type.
   * @param {object} [opt] - Strategy options.
   * @returns {object} Result object with nodes and flags.
   */
  #findEntryNodesForOther = (twig, targetType, opt = {}) => {
    const { leaves } = twig;
    const [leaf] = leaves;
    const { complex, precede, filterLeaves = [] } = opt;
    const compound = filterLeaves.length > 0;
    if (targetType !== TARGET_LINEAL && /host(?:-context)?/.test(leaf.name)) {
      let shadowRoot = null;
      if (
        this.shadow &&
        this.node.nodeType === DOCUMENT_FRAGMENT_NODE &&
        this.evaluateShadowHost(leaf, this.node)
      ) {
        shadowRoot = this.node;
      } else if (
        filterLeaves.length &&
        this.node.nodeType === ELEMENT_NODE &&
        this.evaluateShadowHost(leaf, this.node.shadowRoot)
      ) {
        shadowRoot = this.node.shadowRoot;
      }
      if (shadowRoot) {
        let bool = true;
        const l = filterLeaves.length;
        for (let i = 0; i < l; i++) {
          const filterLeaf = filterLeaves[i];
          switch (filterLeaf.name) {
            case 'host':
            case 'host-context': {
              bool = this.evaluateShadowHost(filterLeaf, shadowRoot);
              break;
            }
            case 'has': {
              bool = this.matchPseudoClassSelector(filterLeaf, shadowRoot, {});
              break;
            }
            default: {
              bool = false;
            }
          }
          if (!bool) {
            break;
          }
        }
        const nodes = [];
        if (bool) {
          nodes.push(shadowRoot);
        }
        return { compound, filtered: nodes.length > 0, nodes, pending: false };
      }
    }
    const earlyResult = this.#checkSelfOrLinealTarget(
      leaves,
      targetType,
      complex,
      compound
    );
    if (earlyResult) {
      return earlyResult;
    }
    if (targetType === TARGET_FIRST) {
      return this.#fallbackToWalkerResult(
        leaves,
        targetType,
        precede,
        compound
      );
    }
    return { compound, filtered: false, nodes: [], pending: true };
  };

  /**
   * Finds entry nodes based on the selector type.
   * @private
   * @param {object} twig - The twig object containing leaves.
   * @param {string} targetType - The target type.
   * @param {object} [opt] - Strategy options.
   * @returns {object} Result object with nodes and flags.
   */
  #findEntryNodes = (twig, targetType, opt = {}) => {
    const { leaves } = twig;
    const [leaf] = leaves;
    const filterLeaves = this.getFilterLeaves(leaves);
    const { complex = false, dir = DIR_PREV } = opt;
    const precede =
      dir === DIR_NEXT &&
      this.node.nodeType === ELEMENT_NODE &&
      this.node !== this.root;
    switch (leaf.type) {
      case PS_ELEMENT_SELECTOR: {
        return this.#findEntryNodesForPseudoElement(
          leaf,
          filterLeaves,
          targetType
        );
      }
      case ID_SELECTOR: {
        return this.#findEntryNodesForId(twig, targetType, {
          complex,
          precede,
          filterLeaves
        });
      }
      case CLASS_SELECTOR: {
        return this.#findEntryNodesForClass(leaves, targetType, {
          complex,
          precede,
          filterLeaves
        });
      }
      case TYPE_SELECTOR: {
        return this.#findEntryNodesForType(leaves, targetType, {
          complex,
          precede,
          filterLeaves
        });
      }
      default: {
        return this.#findEntryNodesForOther(twig, targetType, {
          complex,
          precede,
          filterLeaves
        });
      }
    }
  };

  /**
   * Processes pending items to find matches.
   * @private
   * @param {Set.<object>} pendingItems - Set of pending items to process.
   * @returns {void}
   */
  #processPendingItems = pendingItems => {
    if (!pendingItems.size) {
      return;
    }
    if (!this.#rootWalker) {
      this.#rootWalker = this.createTreeWalker(this.root);
    }
    const node = this.#scoped ? this.node : this.root;
    const walker = this.#rootWalker;
    let nextNode = traverseNode(node, walker);
    while (nextNode) {
      const isWithinScope =
        this.node.nodeType !== ELEMENT_NODE ||
        nextNode === this.node ||
        this.node.contains(nextNode);
      if (isWithinScope) {
        for (const pendingItem of pendingItems) {
          const { leaves } = pendingItem.twig;
          if (this.matchLeaves(leaves, nextNode, this.matchOpts)) {
            const { index } = pendingItem;
            this.#ast[index].filtered = true;
            this.#ast[index].find = true;
            this.#nodes[index].push(nextNode);
          }
        }
      } else if (this.#scoped) {
        break;
      }
      nextNode = walker.nextNode();
    }
  };

  /**
   * Collects all matching nodes into AST nodes array.
   * @private
   * @param {string} targetType - The target type.
   * @returns {Array} Array containing the AST and nodes arrays.
   */
  #collectNodes = targetType => {
    [this.#ast, this.#nodes, this.#selectorAST] = this.#mapper.correspond(
      this.#selector
    );
    const ast = this.#ast.values();
    if (targetType === TARGET_ALL || targetType === TARGET_FIRST) {
      const pendingItems = new Set();
      const hasScope =
        typeof this.#selector === 'string' && this.#selector.includes(':scope');
      const scoped = this.#scoped;
      let i = 0;
      for (const { branch } of ast) {
        const complex = branch.length > 1;
        const { dir, twig } = getTraversalStrategy(
          branch,
          targetType,
          hasScope,
          scoped
        );
        const { compound, filtered, nodes, pending } = this.#findEntryNodes(
          twig,
          targetType,
          { complex, dir }
        );
        if (nodes.length) {
          this.#ast[i].find = true;
          this.#nodes[i] = nodes;
        } else if (pending) {
          pendingItems.add({
            index: i,
            twig
          });
        }
        this.#ast[i].dir = dir;
        this.#ast[i].filtered = filtered || !compound;
        i++;
      }
      this.#processPendingItems(pendingItems);
    } else {
      let i = 0;
      for (const { branch } of ast) {
        const twig = branch[branch.length - 1];
        const complex = branch.length > 1;
        const dir = DIR_PREV;
        const { compound, filtered, nodes } = this.#findEntryNodes(
          twig,
          targetType,
          { complex, dir }
        );
        if (nodes.length) {
          this.#ast[i].find = true;
          this.#nodes[i] = nodes;
        }
        this.#ast[i].dir = dir;
        this.#ast[i].filtered = filtered || !compound;
        i++;
      }
    }
    return [this.#ast, this.#nodes];
  };

  /**
   * Matches a node in the next direction.
   * @private
   * @param {object} node - The starting node.
   * @param {Array.<object>} branch - The selector branch.
   * @param {number} index - The branch index.
   * @param {object} combo - The combinator AST.
   * @returns {object|null} The matched node or null.
   */
  #matchNodeNext = (node, branch, index, combo) => {
    const { combo: nextCombo, leaves } = branch[index];
    const twig = {
      combo,
      leaves
    };
    for (const nextNode of this.yieldCombinatorMatches(twig, node, {
      dir: DIR_NEXT
    })) {
      if (index === branch.length - 1) {
        return nextNode;
      }
      const result = this.#matchNodeNext(
        nextNode,
        branch,
        index + 1,
        nextCombo
      );
      if (result) {
        return result;
      }
    }
    return null;
  };

  /**
   * Recursively checks for a valid backward path.
   * @private
   * @param {object} node - The starting node.
   * @param {Array.<object>} branch - The selector branch.
   * @param {number} index - The current branch index.
   * @param {object} opt - The match options.
   * @returns {boolean} True if a valid path exists, otherwise false.
   */
  #hasValidPathPrev = (node, branch, index, opt) => {
    if (index < 0) {
      return true;
    }
    const twig = branch[index];
    const { combo, leaves } = twig;
    const comboName = combo.name;
    if (comboName === '+') {
      const refNode = node.previousElementSibling;
      if (refNode && this.matchLeaves(leaves, refNode, opt)) {
        if (this.#hasValidPathPrev(refNode, branch, index - 1, opt)) {
          return true;
        }
      }
    } else if (comboName === '~') {
      let refNode = node.previousElementSibling;
      while (refNode) {
        if (this.matchLeaves(leaves, refNode, opt)) {
          if (this.#hasValidPathPrev(refNode, branch, index - 1, opt)) {
            return true;
          }
        }
        refNode = refNode.previousElementSibling;
      }
    } else if (comboName === '>') {
      const parentNode = node.parentNode;
      if (parentNode && this.matchLeaves(leaves, parentNode, opt)) {
        if (this.#hasValidPathPrev(parentNode, branch, index - 1, opt)) {
          return true;
        }
      }
    } else {
      let refNode = node.parentNode;
      while (refNode) {
        if (this.matchLeaves(leaves, refNode, opt)) {
          if (this.#hasValidPathPrev(refNode, branch, index - 1, opt)) {
            return true;
          }
        }
        refNode = refNode.parentNode;
      }
    }
    return false;
  };

  /**
   * Depth-first search for tracking complex combinator branches forward.
   * @private
   * @param {object} node - The current DOM node.
   * @param {number} index - The current index in the selector branch.
   * @param {object} currentCombo - The current combinator AST node.
   * @param {Array.<object>} branch - The selector branch array.
   * @param {number} lastIndex - The last index of the branch.
   * @param {Set.<object>} matchedNodes - The set accumulating matched nodes.
   * @param {string} dir - The traversal direction.
   * @returns {void}
   */
  #dfsComplexBranchNext = (
    node,
    index,
    currentCombo,
    branch,
    lastIndex,
    matchedNodes,
    dir
  ) => {
    const { combo: nextCombo, leaves } = branch[index];
    const twig = { combo: currentCombo, leaves };
    for (const nextNode of this.yieldCombinatorMatches(twig, node, { dir })) {
      if (index === lastIndex) {
        matchedNodes.add(nextNode);
      } else {
        this.#dfsComplexBranchNext(
          nextNode,
          index + 1,
          nextCombo,
          branch,
          lastIndex,
          matchedNodes,
          dir
        );
      }
    }
  };

  /**
   * Processes complex branch for all matches.
   * @private
   * @param {Array.<object>} branch - The selector branch.
   * @param {Array.<object>} entryNodes - The entry nodes.
   * @param {string} dir - The traversal direction.
   * @returns {Set.<object>} Set of matched nodes.
   */
  #processComplexBranchAll = (branch, entryNodes, dir) => {
    const matchedNodes = new Set();
    const branchLen = branch.length;
    const lastIndex = branchLen - 1;
    if (dir === DIR_NEXT) {
      const { combo: firstCombo } = branch[0];
      for (const node of entryNodes) {
        this.#dfsComplexBranchNext(
          node,
          1,
          firstCombo,
          branch,
          lastIndex,
          matchedNodes,
          dir
        );
      }
    } else {
      for (let i = 0, len = entryNodes.length; i < len; i++) {
        const node = entryNodes[i];
        if (
          this.#hasValidPathPrev(node, branch, lastIndex - 1, this.matchOpts)
        ) {
          matchedNodes.add(node);
        }
      }
    }
    return matchedNodes;
  };

  /**
   * Processes complex branch first match in the forward direction.
   * @private
   * @param {Array.<object>} branch - The selector branch.
   * @param {Array.<object>} entryNodes - The entry nodes.
   * @param {number} lastIndex - The last index of the branch.
   * @param {string} targetType - The target type.
   * @returns {object|null} The matched node or null if not found.
   */
  #processComplexBranchFirstNext = (
    branch,
    entryNodes,
    lastIndex,
    targetType
  ) => {
    const { combo: entryCombo } = branch[0];
    for (const node of entryNodes) {
      const matchedNode = this.#matchNodeNext(node, branch, 1, entryCombo);
      if (matchedNode) {
        if (this.node.nodeType === ELEMENT_NODE) {
          if (matchedNode !== this.node && this.node.contains(matchedNode)) {
            return matchedNode;
          }
        } else {
          return matchedNode;
        }
      }
    }
    const { leaves: entryLeaves } = branch[0];
    const [entryNode] = entryNodes;
    if (this.node.contains(entryNode)) {
      let [refNode] = this.#findNodeWalker(entryLeaves, entryNode, {
        targetType
      });
      while (refNode) {
        const matchedNode = this.#matchNodeNext(refNode, branch, 1, entryCombo);
        if (matchedNode) {
          return matchedNode;
        }
        [refNode] = this.#findNodeWalker(entryLeaves, refNode, {
          targetType,
          force: true
        });
      }
    }
    return null;
  };

  /**
   * Processes complex branch first match in the backward direction.
   * @private
   * @param {Array.<object>} branch - The selector branch.
   * @param {Array.<object>} entryNodes - The entry nodes.
   * @param {number} lastIndex - The last index of the branch.
   * @param {string} targetType - The target type.
   * @returns {object|null} The matched node or null if not found.
   */
  #processComplexBranchFirstPrev = (
    branch,
    entryNodes,
    lastIndex,
    targetType
  ) => {
    for (let i = 0, len = entryNodes.length; i < len; i++) {
      const node = entryNodes[i];
      if (this.#hasValidPathPrev(node, branch, lastIndex - 1, this.matchOpts)) {
        return node;
      }
    }
    if (targetType === TARGET_FIRST) {
      const { leaves: entryLeaves } = branch[lastIndex];
      const entryNode = entryNodes[0];
      let [refNode] = this.#findNodeWalker(entryLeaves, entryNode, {
        targetType
      });
      while (refNode) {
        if (
          this.#hasValidPathPrev(refNode, branch, lastIndex - 1, this.matchOpts)
        ) {
          return refNode;
        }
        [refNode] = this.#findNodeWalker(entryLeaves, refNode, {
          targetType,
          force: true
        });
      }
    }
    return null;
  };

  /**
   * Processes complex branch for the first match.
   * @private
   * @param {Array.<object>} branch - The selector branch.
   * @param {Array.<object>} entryNodes - The entry nodes.
   * @param {string} dir - The traversal direction.
   * @param {string} targetType - The target type.
   * @returns {object|null} The matched node or null.
   */
  #processComplexBranchFirst = (branch, entryNodes, dir, targetType) => {
    const branchLen = branch.length;
    const lastIndex = branchLen - 1;
    if (dir === DIR_NEXT) {
      return this.#processComplexBranchFirstNext(
        branch,
        entryNodes,
        lastIndex,
        targetType
      );
    } else {
      return this.#processComplexBranchFirstPrev(
        branch,
        entryNodes,
        lastIndex,
        targetType
      );
    }
  };
}
