import {
  Component,
  inject,
  signal,
  ChangeDetectionStrategy,
} from '@angular/core';
import {
  ActivatedRoute,
  NavigationEnd,
  Router,
  RouterOutlet,
} from '@angular/router';
import { Toast } from '@openng/optimus-ui/toast';
import { TranslatePipe, TranslateService } from '@ngx-translate/core';
import { combineLatest, filter, map, Observable, startWith } from 'rxjs';
import { toSignal } from '@angular/core/rxjs-interop';
import { MenuItem } from '@openng/optimus-ui/api';
import { AsyncPipe } from '@angular/common';
import { Button } from '@openng/optimus-ui/button';
import { Tag } from '@openng/optimus-ui/tag';
import { Dialog } from '@openng/optimus-ui/dialog';
import { DeployGuidelineUrl } from './app.consts';
import { FormsModule } from '@angular/forms';
import { Breadcrumb } from '@openng/optimus-ui/breadcrumb';
import { IRouteData } from '@shared/interfaces/route-data.interface';
import { AppStore } from './app.store';
import { MenuComponent } from '@shared/components/menu/menu.component';

@Component({
  selector: 'app-root',
  imports: [
    RouterOutlet,
    Toast,
    AsyncPipe,
    Button,
    TranslatePipe,
    Tag,
    Dialog,
    FormsModule,
    Breadcrumb,
    MenuComponent,
  ],
  templateUrl: './app.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl: './app.scss',
})
export class App {
  private readonly translateService = inject(TranslateService);
  private readonly router = inject(Router);
  private readonly activatedRoute = inject(ActivatedRoute);
  protected readonly appStore = inject(AppStore);

  /**
   * Whether to show new version dialog
   */
  protected readonly showNewVersionDialog = signal<boolean>(false);
  /**
   * Breadcrumbs list
   */
  protected readonly breadcrumbs$: Observable<MenuItem[]> = combineLatest([
    this.router.events.pipe(
      filter((ev) => ev instanceof NavigationEnd),
      map(() => this.activatedRoute),
      startWith(this.activatedRoute),
    ),
    this.translateService.stream('BREADCRUMBS'),
  ]).pipe(
    map(([ar, t]) => {
      const breadcrumbs: MenuItem[] = [];

      let fisrtChild = ar.firstChild?.snapshot;
      let url = '';

      while (fisrtChild) {
        const routeUrl = fisrtChild.url
          .map((segment) => segment.path)
          .filter(Boolean)
          .join('/');

        url = routeUrl ? `${url}/${routeUrl}` : url;
        const data = fisrtChild.data as IRouteData;
        const breadcrumb = data?.['breadcrumb'];
        const breadcrumbIcon = data?.['breadcrumbIcon'];

        if (breadcrumb || breadcrumbIcon) {
          breadcrumbs.push({
            label: t[breadcrumb],
            icon: breadcrumbIcon,
            routerLink: url,
          });
        }

        fisrtChild = fisrtChild.firstChild;
      }

      return breadcrumbs;
    }),
  );

  protected readonly isToolbarVisible = toSignal<boolean>(
    this.router.events.pipe(
      map(() => {
        return !['/', '/auth'].includes(this.router.url);
      }),
      startWith(!['/', '/auth'].includes(this.router.url)),
    ),
  );

  protected openDeployGuideline(): void {
    window.open(DeployGuidelineUrl, '_blank');
  }

  protected openReleaseNotes(): void {
    const url = this.appStore.update().release_url;
    window.open(url, '_blank');
  }
}
