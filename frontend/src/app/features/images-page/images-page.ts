import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { ImagesPageTable } from './images-page-table/images-page-table';
import { RouterLink } from '@angular/router';
import { TranslatePipe } from '@ngx-translate/core';
import { AccordionModule } from 'primeng/accordion';
import { ButtonModule } from 'primeng/button';
import { TagModule } from 'primeng/tag';
import { finalize } from 'rxjs';
import { ToastService } from 'src/app/core/services/toast.service';
import { HostsApiService } from 'src/app/entities/hosts/hosts-api.service';
import { IHostInfo } from 'src/app/entities/hosts/hosts-interface';
import { NoHosts } from 'src/app/shared/components/no-hosts/no-hosts';

@Component({
  selector: 'app-images-page',
  imports: [
    ImagesPageTable,
    AccordionModule,
    TagModule,
    ButtonModule,
    RouterLink,
    TranslatePipe,
    NoHosts,
  ],
  templateUrl: './images-page.html',
  styleUrl: './images-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ImagesPage {
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
