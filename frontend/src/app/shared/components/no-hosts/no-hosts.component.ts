import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterLink } from '@angular/router';
import { TranslatePipe } from '@ngx-translate/core';
import { Button } from '@openng/optimus-ui/button';

@Component({
  selector: 'app-no-hosts',
  imports: [TranslatePipe, RouterLink, Button],
  templateUrl: './no-hosts.component.html',
  styleUrl: './no-hosts.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class NoHostsComponent {}
