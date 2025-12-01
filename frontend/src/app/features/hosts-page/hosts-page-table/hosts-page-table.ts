import { ChangeDetectionStrategy, Component, inject, resource } from '@angular/core';
import { RouterLink } from '@angular/router';
import { TranslatePipe } from '@ngx-translate/core';
import { ButtonModule } from 'primeng/button';
import { ButtonGroupModule } from 'primeng/buttongroup';
import { IconFieldModule } from 'primeng/iconfield';
import { InputIconModule } from 'primeng/inputicon';
import { InputTextModule } from 'primeng/inputtext';
import { TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';
import { ToolbarModule } from 'primeng/toolbar';
import { catchError, firstValueFrom, of } from 'rxjs';
import { ToastService } from 'src/app/core/services/toast.service';
import { HostsApiService } from 'src/app/entities/hosts/hosts-api.service';
import { ICreateHost } from 'src/app/entities/hosts/hosts-interface';
import { HostStatus } from 'src/app/shared/components/host-status/host-status';

@Component({
  selector: 'app-host-page-table',
  imports: [
    TableModule,
    ButtonModule,
    TranslatePipe,
    RouterLink,
    IconFieldModule,
    InputIconModule,
    ButtonGroupModule,
    InputTextModule,
    TagModule,
    HostStatus,
    ToolbarModule,
  ],
  templateUrl: './hosts-page-table.html',
  styleUrl: './hosts-page-table.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HostsPageTable {
  private readonly hostsApiService = inject(HostsApiService);
  private readonly toastService = inject(ToastService);

  public readonly list = resource<ICreateHost[], {}>({
    loader: () =>
      firstValueFrom(
        this.hostsApiService.list().pipe(
          catchError((error) => {
            this.toastService.error(error);
            return of([]);
          }),
        ),
      ),
    defaultValue: [],
  });
}
