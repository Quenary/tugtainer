import { ChangeDetectionStrategy, Component, HostListener, inject } from '@angular/core';
import { Router } from '@angular/router';
import { TranslatePipe } from '@ngx-translate/core';

@Component({
  selector: 'app-logo',
  imports: [TranslatePipe],
  templateUrl: './logo.component.html',
  styleUrl: './logo.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LogoComponent {
  private readonly router = inject(Router);

  @HostListener('click')
  onClick(): void {
    this.router.navigate(['/']);
  }
}
