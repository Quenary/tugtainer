import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  OnInit,
  signal,
} from '@angular/core';
import { ContainersPageTable } from './containers-page-table/containers-page-table';
import { HostsApiService } from 'src/app/entities/hosts/hosts-api.service';
import { ToastService } from 'src/app/core/services/toast.service';
import { IHostInfo } from 'src/app/entities/hosts/hosts-interface';
import { finalize } from 'rxjs';
import { AccordionModule } from 'primeng/accordion';
import { TagModule } from 'primeng/tag';
import { ButtonModule } from 'primeng/button';
import { RouterLink } from '@angular/router';
import { TranslatePipe } from '@ngx-translate/core';

@Component({
  selector: 'app-containers-page',
  imports: [
    ContainersPageTable,
    AccordionModule,
    TagModule,
    ButtonModule,
    RouterLink,
    TranslatePipe,
  ],
  templateUrl: './containers-page.html',
  styleUrl: './containers-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ContainersPage implements OnInit {
  private readonly hostsApiService = inject(HostsApiService);
  private readonly toastService = inject(ToastService);

  public readonly isLoading = signal<boolean>(false);
  public readonly hosts = signal<IHostInfo[]>([]);
  public readonly accordionValue = computed(() => {
    const hosts = this.hosts();
    return hosts.filter((h) => h.enabled).map((h) => h.id);
  });

  ngOnInit(): void {
    this.updateHostList();
  }

  updateHostList(): void {
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
          this.hosts.set(list);
        },
        error: (error) => {
          this.toastService.error(error);
        },
      });
  }
}
