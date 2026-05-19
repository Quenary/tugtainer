import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { TranslatePipe } from '@ngx-translate/core';
import { SkeletonModule } from 'primeng/skeleton';
import { TagModule } from 'primeng/tag';
import { TooltipModule } from 'primeng/tooltip';
import { IHostEntity } from 'src/app/features/hosts/hosts.store';

@Component({
  selector: 'app-host-status',
  imports: [TagModule, TooltipModule, TranslatePipe, SkeletonModule],
  templateUrl: './host-status.component.html',
  styleUrl: './host-status.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HostStatusComponent {
  public readonly host = input.required<IHostEntity>();
}
