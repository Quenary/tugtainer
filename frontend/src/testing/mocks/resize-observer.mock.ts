import { Mocked, vi } from 'vitest';

export class ResizeObserverMock implements Mocked<ResizeObserver> {
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
}
