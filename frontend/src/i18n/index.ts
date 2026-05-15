import { pt } from "./pt";

const catalog = pt;

export type Catalog = typeof pt;

export function t(key: string): string {
  const parts = key.split(".");
  let cur: unknown = catalog;
  for (const part of parts) {
    if (typeof cur === "object" && cur !== null && part in cur) {
      cur = (cur as Record<string, unknown>)[part];
    } else {
      return key;
    }
  }
  return typeof cur === "string" ? cur : key;
}

export function useT(): (key: string) => string {
  return t;
}
