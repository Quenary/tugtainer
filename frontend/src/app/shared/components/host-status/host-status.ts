import { ChangeDetectionStrategy, Component, inject, input, resource } from '@angular/core';
import { TranslatePipe } from '@ngx-translate/core';
import { SkeletonModule } from 'primeng/skeleton';
import { TagModule } from 'primeng/tag';
import { TooltipModule } from 'primeng/tooltip';
import { lastValueFrom } from 'rxjs';
import { HostsApiService } from 'src/app/entities/hosts/hosts-api.service';
import { IHostInfo } from 'src/app/entities/hosts/hosts-interface';

@Component({
  selector: 'app-host-status',
  imports: [TagModule, TooltipModule, TranslatePipe, SkeletonModule],
  templateUrl: './host-status.html',
  styleUrl: './host-status.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HostStatus {
  private readonly hostsApiService = inject(HostsApiService);

  public readonly host = input<IHostInfo>();

  public readonly status = resource({
    params: () => ({ host: this.host() }),
    loader: (params) => lastValueFrom(this.hostsApiService.status(params.params.host.id)),
  });
}
