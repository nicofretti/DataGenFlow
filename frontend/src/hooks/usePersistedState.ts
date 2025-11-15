import { useEffect, useState } from "react";

/**
 * hook to persist state in localStorage with type safety
 * abstracts localStorage access to prevent coupling
 */
export function usePersistedState<T>(key: string, defaultValue: T): [T, (value: T) => void] {
  const [value, setValue] = useState<T>(() => {
    try {
      const stored = localStorage.getItem(key);
      if (stored === null) {
        return defaultValue;
      }
      return JSON.parse(stored) as T;
    } catch (error) {
      console.error(`failed to parse localStorage key "${key}":`, error);
      return defaultValue;
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch (error) {
      console.error(`failed to save to localStorage key "${key}":`, error);
    }
  }, [key, value]);

  return [value, setValue];
}
