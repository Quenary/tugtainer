import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { TranslatePipe } from '@ngx-translate/core';
import { Skeleton } from '@openng/optimus-ui/skeleton';
import { Tag } from '@openng/optimus-ui/tag';
import { Tooltip } from '@openng/optimus-ui/tooltip';
import { IHostEntity } from 'src/app/features/hosts/hosts.store';

@Component({
  selector: 'app-host-status',
  imports: [Tag, Tooltip, TranslatePipe, Skeleton],
  templateUrl: './host-status.component.html',
  styleUrl: './host-status.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HostStatusComponent {
  public readonly host = input.required<IHostEntity>();
}
