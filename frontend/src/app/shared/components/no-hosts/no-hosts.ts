import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterLink } from '@angular/router';
import { TranslatePipe } from '@ngx-translate/core';
import { ButtonModule } from 'primeng/button';

@Component({
  selector: 'app-no-hosts',
  imports: [TranslatePipe, RouterLink, ButtonModule],
  templateUrl: './no-hosts.html',
  styleUrl: './no-hosts.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class NoHosts {}
