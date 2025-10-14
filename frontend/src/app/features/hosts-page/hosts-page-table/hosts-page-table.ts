import { ChangeDetectionStrategy, Component, inject, OnInit, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { TranslatePipe } from '@ngx-translate/core';
import { ButtonModule } from 'primeng/button';
import { ButtonGroupModule } from 'primeng/buttongroup';
import { IconFieldModule } from 'primeng/iconfield';
import { InputIconModule } from 'primeng/inputicon';
import { InputTextModule } from 'primeng/inputtext';
import { TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';
import { finalize } from 'rxjs';
import { ToastService } from 'src/app/core/services/toast.service';
import { HostsApiService } from 'src/app/entities/hosts/hosts-api.service';
import { ICreateHost } from 'src/app/entities/hosts/hosts-interface';

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
  ],
  templateUrl: './hosts-page-table.html',
  styleUrl: './hosts-page-table.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HostsPageTable implements OnInit {
  private readonly hostsApiService = inject(HostsApiService);
  private readonly toastService = inject(ToastService);

  public readonly isLoading = signal<boolean>(false);
  public readonly list = signal<ICreateHost[]>([]);

  ngOnInit(): void {
    this.updateList();
  }

  public updateList(): void {
    this.isLoading.set(true);
    this.hostsApiService
      .list()
      .pipe(
        finalize(() => {
          this.isLoading.set(false);
        }),
      )
      .subscribe({
        next: (list) => {
          this.list.set(list);
        },
        error: (error) => {
          this.toastService.error(error);
        },
      });
  }
}
