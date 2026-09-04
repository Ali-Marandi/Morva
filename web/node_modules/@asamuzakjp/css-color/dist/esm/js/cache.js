import { LRUCache } from "lru-cache";
//#region src/js/cache.ts
/**
* cache
*/
var CACHE_SIZE = 4096;
/**
* CacheItem
*/
var CacheItem = class {
	#item;
	constructor(item) {
		this.#item = item;
	}
	get item() {
		return this.#item;
	}
};
var lruCache = new LRUCache({ max: CACHE_SIZE });
/**
* set cache
* @param key - cache key
* @param value - value to cache
* @returns void
*/
var setCache = (key, value) => {
	if (!key) return;
	if (value instanceof CacheItem) lruCache.set(key, value);
	else lruCache.set(key, new CacheItem(value));
};
/**
* get cache
* @param key - cache key
* @returns cached item or false otherwise
*/
var getCache = (key) => {
	if (!key) return false;
	const item = lruCache.get(key);
	if (item !== void 0) return item;
	return false;
};
/**
* helper function to sort object keys alphabetically
* @param obj - Object
* @returns stringified JSON
*/
var stringifySorted = (obj) => {
	const keys = Object.keys(obj);
	if (keys.length === 0) return "";
	keys.sort();
	let result = "";
	for (const key of keys) result += `${key}:${JSON.stringify(obj[key])};`;
	return result;
};
/**
* create cache key
* @param keyData - key data
* @param [opt] - options
* @returns cache key
*/
var createCacheKey = (keyData, opt = {}) => {
	if (!keyData || opt.customProperty && typeof opt.customProperty.callback === "function" || opt.dimension && typeof opt.dimension.callback === "function") return "";
	const namespace = keyData.namespace || "";
	const name = keyData.name || "";
	const value = keyData.value || "";
	if (!namespace && !name && !value) return "";
	return `${`${namespace}:${name}:${value}`}::${`${opt.format || ""}|${opt.colorSpace || ""}|${opt.colorScheme || ""}|${opt.currentColor || ""}|${opt.d50 ? "1" : "0"}|${opt.nullable ? "1" : "0"}|${opt.preserveComment ? "1" : "0"}|${opt.delimiter || ""}`}::${opt.customProperty ? stringifySorted(opt.customProperty) : ""}::${opt.dimension ? stringifySorted(opt.dimension) : ""}`;
};
//#endregion
export { CacheItem, createCacheKey, getCache, lruCache, setCache };

//# sourceMappingURL=cache.js.map