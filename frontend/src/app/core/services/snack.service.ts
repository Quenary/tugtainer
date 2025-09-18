import { HttpErrorResponse } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { MatSnackBar } from '@angular/material/snack-bar';
import { TranslateService } from '@ngx-translate/core';

@Injectable({
  providedIn: 'root',
})
export class SnackService {
  private readonly matSnackBar = inject(MatSnackBar);
  private readonly translateService = inject(TranslateService);

  /**
   * Show error snack
   * @param error error
   * @param action action button text
   */
  error(
    error: HttpErrorResponse | Error | string | unknown,
    action: string = this.translateService.instant('GENERAL.CLOSE')
  ): void {
    let message: string = '';
    if (error instanceof HttpErrorResponse) {
      message = this.translateService.instant('GENERAL.REQUEST_ERROR');
      message += `: ${error.status} ${error.statusText}`;
      if (typeof error.error?.detail === 'string') {
        message += ` - ${error.error.detail}`;
      }
    } else if (error instanceof Error) {
      message = error.message;
    } else if (typeof error === 'string') {
      message = error;
    } else {
      try {
        message = JSON.stringify(error);
      } catch (e) {
        message = this.translateService.instant('GENERAL.UNKNOWN_ERROR');
        console.error(e);
      }
    }
    this.matSnackBar.open(message, action, {
      duration: 8000,
      panelClass: ['mat-snack-error', 'mat-snack-no-overflow'],
      verticalPosition: 'top',
    });
  }

  /**
   * Show success snack
   * @param message message text
   * @param action action button text
   */
  success(message: string, action: string = this.translateService.instant('GENERAL.CLOSE')): void {
    this.matSnackBar.open(message, action, {
      duration: 4000,
      panelClass: ['mat-snack-success', 'mat-snack-no-overflow'],
      verticalPosition: 'top',
    });
  }
}
