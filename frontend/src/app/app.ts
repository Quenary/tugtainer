import { Component, inject, signal } from '@angular/core';
import { Router, RouterOutlet } from '@angular/router';
import { ToastModule } from 'primeng/toast';
import { TranslatePipe, TranslateService } from '@ngx-translate/core';
import { AuthApiService } from './entities/auth/auth-api.service';
import { catchError, debounceTime, finalize, map, Observable, of, retry, startWith } from 'rxjs';
import { toSignal } from '@angular/core/rxjs-interop';
import { MenuItem } from 'primeng/api';
import { AsyncPipe } from '@angular/common';
import { PublicApiService } from './entities/public/public-api.service';
import { ContainersApiService } from './entities/containers/containers-api.service';
import { ButtonModule } from 'primeng/button';
import { TagModule } from 'primeng/tag';
import { DialogModule } from 'primeng/dialog';
import { Logo } from './shared/components/logo/logo';
import { DrawerModule } from 'primeng/drawer';
import { PanelMenuModule } from 'primeng/panelmenu';
import { ToolbarModule } from 'primeng/toolbar';

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
  private readonly containersApiService = inject(ContainersApiService);

  public readonly showNewVersionDialog = signal<boolean>(false);
  public readonly newVersionDialogText = `
docker stop tugtainer

docker rm tugtainer

docker pull quenary/tugtainer:latest

docker run -d -p 9412:80 \\
  --name=tugtainer \\
  --restart=unless-stopped \\
  -v tugtainer_data:/tugtainer \\
  -v /var/run/docker.sock:/var/run/docker.sock \\
  quenary/tugtainer:latest
`;
  public readonly version$ = this.publicApiService.getVersion().pipe(
    retry({ count: 3, delay: 500 }),
    catchError(() => of({ image_version: 'unknown' })),
  );
  public readonly isUpdateAvailable$ = this.containersApiService.isUpdateAvailableSelf().pipe(
    retry({ count: 3, delay: 500 }),
    catchError(() => of(false)),
  );
  public readonly menuItems$: Observable<MenuItem[]> = this.translateService.get('MENU').pipe(
    map((translates) => {
      return <MenuItem[]>[
        {
          label: translates.CONTAINERS,
          routerLink: '/containers',
          icon: 'pi pi-box',
        },
        {
          label: translates.IMAGES,
          routerLink: '/images',
          icon: 'pi pi-file',
        },
        {
          label: translates.SETTINGS,
          routerLink: '/settings',
          icon: 'pi pi-cog',
        },
        {
          label: translates.GITHUB,
          url: 'https://github.com/Quenary/tugtainer',
          target: '_blank',
          icon: 'pi pi-github',
        },
      ];
    }),
  );
  public readonly menuOpened = signal<boolean>(false);

  public readonly isToolbarVisible = toSignal<boolean>(
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
