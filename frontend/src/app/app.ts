import { Component, inject, resource, signal } from '@angular/core';
import { Router, RouterOutlet } from '@angular/router';
import { ToastModule } from 'primeng/toast';
import { TranslatePipe, TranslateService } from '@ngx-translate/core';
import { AuthApiService } from './entities/auth/auth-api.service';
import {
  catchError,
  debounceTime,
  finalize,
  firstValueFrom,
  map,
  Observable,
  of,
  retry,
  startWith,
  switchMap,
  throwError,
} from 'rxjs';
import { toSignal } from '@angular/core/rxjs-interop';
import { MenuItem } from 'primeng/api';
import { AsyncPipe } from '@angular/common';
import { PublicApiService } from './entities/public/public-api.service';
import { ButtonModule } from 'primeng/button';
import { TagModule } from 'primeng/tag';
import { DialogModule } from 'primeng/dialog';
import { Logo } from './shared/components/logo/logo';
import { DrawerModule } from 'primeng/drawer';
import { PanelMenuModule } from 'primeng/panelmenu';
import { ToolbarModule } from 'primeng/toolbar';
import { DeployGuidelineUrl } from './app.consts';
import { ToastService } from './core/services/toast.service';
import { IsUpdateAvailableResponseBody } from './entities/public/public-interface';

@Component({
  selector: 'app-root',
  imports: [
    RouterOutlet,
    ToastModule,
    AsyncPipe,
    ButtonModule,
    TranslatePipe,
    TagModule,
    DialogModule,
    Logo,
    DrawerModule,
    PanelMenuModule,
    ToolbarModule,
  ],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App {
  private readonly authApiService = inject(AuthApiService);
  private readonly translateService = inject(TranslateService);
  private readonly router = inject(Router);
  private readonly publicApiService = inject(PublicApiService);
  private readonly toastService = inject(ToastService);

  protected readonly showNewVersionDialog = signal<boolean>(false);
  /**
   * Is auth disabled
   */
  protected readonly isAuthDisabled = resource({
    defaultValue: false,
    loader: () =>
      firstValueFrom(
        this.authApiService.isDisabled().pipe(
          retry(1),
          catchError((error) => {
            this.toastService.error(error);
            return throwError(() => error);
          }),
        ),
      ),
  });
  protected readonly version = resource({
    loader: () =>
      firstValueFrom(
        this.publicApiService.getVersion().pipe(
          retry({ count: 1, delay: 500 }),
          catchError(() => of({ image_version: 'unknown' })),
        ),
      ),
  });
  protected readonly isUpdateAvailable = resource({
    loader: () =>
      firstValueFrom(
        this.publicApiService.isUpdateAvailable().pipe(
          retry({ count: 1, delay: 500 }),
          catchError(() =>
            of(<IsUpdateAvailableResponseBody>{
              is_available: false,
              release_url: null,
            }),
          ),
        ),
      ),
  });
  protected readonly menuItems$: Observable<MenuItem[]> = this.translateService.onLangChange.pipe(
    startWith({}),
    switchMap(() => this.translateService.get('MENU')),
    map(
      (t) =>
        <MenuItem[]>[
          {
            label: t.HOSTS,
            routerLink: '/hosts',
            icon: 'pi pi-server',
          },
          {
            label: t.CONTAINERS,
            routerLink: '/containers',
            icon: 'pi pi-box',
          },
          {
            label: t.IMAGES,
            routerLink: '/images',
            icon: 'pi pi-file',
          },
          {
            label: t.SETTINGS,
            routerLink: '/settings',
            icon: 'pi pi-cog',
          },
          {
            label: t.GITHUB,
            url: 'https://github.com/Quenary/tugtainer',
            target: '_blank',
            icon: 'pi pi-github',
          },
        ],
    ),
  );
  protected readonly menuOpened = signal<boolean>(false);

  protected readonly isToolbarVisible = toSignal<boolean>(
    this.router.events.pipe(
      debounceTime(100),
      map(() => {
        const exclude = ['/', '/auth'];
        return !exclude.includes(this.router.url);
      }),
      startWith(false),
    ),
  );

  protected logout(): void {
    this.authApiService
      .logout()
      .pipe(
        finalize(() => {
          this.router.navigate(['/auth']);
        }),
      )
      .subscribe();
  }

  protected openDeployGuideline(): void {
    window.open(DeployGuidelineUrl, '_blank');
  }

  protected openReleaseNotes(): void {
    window.open(this.isUpdateAvailable.value().release_url, '_blank');
  }
}
