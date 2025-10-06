import { inject, Injectable } from '@angular/core';
import { TranslateService } from '@ngx-translate/core';
import { MessageService } from 'primeng/api';
import { parseError } from 'src/app/shared/functions/parse-error.function';

@Injectable({
  providedIn: 'root',
})
export class ToastService {
  private readonly messageService = inject(MessageService);
  private readonly translateService = inject(TranslateService);

  error(error: unknown, summary: string = this.translateService.instant('GENERAL.ERROR')): void {
    this.messageService.add({
      severity: 'error',
      summary,
      detail: parseError(error),
    });
  }

  success(
    summary: string = this.translateService.instant('GENERAL.SUCCESS'),
    detail: string = null,
  ): void {
    this.messageService.add({
      severity: 'success',
      summary,
      detail,
    });
  }
}
