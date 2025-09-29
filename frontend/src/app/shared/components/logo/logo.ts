import { ChangeDetectionStrategy, Component, HostListener, inject } from '@angular/core';
import { Router } from '@angular/router';
import { TranslateModule } from '@ngx-translate/core';

@Component({
  selector: 'app-logo',
  imports: [TranslateModule],
  templateUrl: './logo.html',
  styleUrl: './logo.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Logo {
  private readonly router = inject(Router);

  @HostListener('click')
  onClick(): void {
    this.router.navigate(['/']);
  }
}
