import { Component, inject } from '@angular/core';
import { Router, RouterOutlet } from '@angular/router';
import { ToastModule } from 'primeng/toast';
import { MenubarModule } from 'primeng/menubar';
import { TranslateService } from '@ngx-translate/core';
import { AuthApiService } from './entities/auth/auth-api.service';
import {
  catchError,
  combineLatest,
  debounceTime,
  finalize,
  map,
  Observable,
  of,
  retry,
  startWith,
} from 'rxjs';
import { toSignal } from '@angular/core/rxjs-interop';
import { MenuItem } from 'primeng/api';
import { AsyncPipe } from '@angular/common';
import { PublicApiService } from './entities/public/public-api.service';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, ToastModule, AsyncPipe, MenubarModule],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App {
  private readonly authApiService = inject(AuthApiService);
  private readonly translateService = inject(TranslateService);
  private readonly router = inject(Router);
  private readonly publicApiService = inject(PublicApiService);

  public readonly menuItems$: Observable<MenuItem[]> = combineLatest([
    this.translateService.get('MENU'),
    this.publicApiService.getVersion().pipe(
      retry({ count: 3, delay: 500 }),
      catchError(() => of({ image_version: 'unknown' })),
    ),
  ]).pipe(
    map(([translates, version]) => {
      return <MenuItem[]>[
        {
          label: translates.CONTAINERS,
          routerLink: '/containers',
          icon: 'pi pi-box',
        },
        {
          label: translates.SETTINGS,
          routerLink: '/settings',
          icon: 'pi pi-cog',
        },
        {
          label: translates.GITHUB,
          url: 'https://github.com/Quenary/dockobserver',
          target: '_blank',
          icon: 'pi pi-github',
        },
        {
          label: version.image_version,
          disabled: true,
          style: { marginLeft: 'auto' },
        },
        {
          label: translates.LOGOUT,
          command: () => this.logout(),
          icon: 'pi pi-sign-out',
        },
      ];
    }),
  );

  public readonly isMenuVisible = toSignal<boolean>(
    this.router.events.pipe(
      debounceTime(100),
      map(() => {
        const exclude = ['/', '/auth'];
        return !exclude.includes(this.router.url);
      }),
      startWith(false),
    ),
  );

  public logout(): void {
    this.authApiService
      .logout()
      .pipe(
        finalize(() => {
          this.router.navigate(['/auth']);
        }),
      )
      .subscribe();
  }
}
