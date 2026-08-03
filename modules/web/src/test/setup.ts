import "@testing-library/jest-dom/vitest";

/**
 * Node 22+ may expose a non-functional global `localStorage` (requires
 * `--localstorage-file`) that breaks jsdom Storage. Always install an
 * in-memory Storage on both `window` and `globalThis` for Vitest.
 */
class MemoryStorage implements Storage {
  #map = new Map<string, string>();

  get length(): number {
    return this.#map.size;
  }

  clear(): void {
    this.#map.clear();
  }

  getItem(key: string): string | null {
    return this.#map.has(key) ? (this.#map.get(key) as string) : null;
  }

  key(index: number): string | null {
    return [...this.#map.keys()][index] ?? null;
  }

  removeItem(key: string): void {
    this.#map.delete(key);
  }

  setItem(key: string, value: string): void {
    this.#map.set(String(key), String(value));
  }
}

const local = new MemoryStorage();
const session = new MemoryStorage();

Object.defineProperty(window, "localStorage", { configurable: true, value: local });
Object.defineProperty(window, "sessionStorage", { configurable: true, value: session });
Object.defineProperty(globalThis, "localStorage", { configurable: true, value: local });
Object.defineProperty(globalThis, "sessionStorage", { configurable: true, value: session });
