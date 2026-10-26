import { Injectable } from '@angular/core';

/**
 * Wrapper around location.reload, so it can be replaced in tests
 */
@Injectable({
  providedIn: 'root',
})
export class PageReloadService {
  reload(): void {
    window.location.reload();
  }
}
