import {
  Component,
  inject,
  signal,
  computed,
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
import { filter, map, startWith } from 'rxjs';
import { toSignal } from '@angular/core/rxjs-interop';
import { MenuItem } from '@openng/optimus-ui/api';
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
   * Emits after each successful navigation so breadcrumbs can be recomputed
   * from the activated route tree.
   */
  private readonly navigationEnd = toSignal(
    this.router.events.pipe(
      filter((event): event is NavigationEnd => event instanceof NavigationEnd),
    ),
  );
  private readonly breadcrumbLabels = toSignal(
    this.translateService.stream('BREADCRUMBS'),
    { initialValue: {} as Record<string, string> },
  );
  /**
   * Breadcrumbs list
   */
  protected readonly breadcrumbs = computed(() => {
    this.navigationEnd();
    return this.buildBreadcrumbs(this.activatedRoute, this.breadcrumbLabels());
  });

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

  private buildBreadcrumbs(
    route: ActivatedRoute,
    labels: Record<string, string>,
  ): MenuItem[] {
    const breadcrumbs: MenuItem[] = [];
    let current = route.firstChild;
    let url = '';

    while (current) {
      const routeUrl = current.snapshot.url
        .map((segment) => segment.path)
        .filter(Boolean)
        .join('/');

      url = routeUrl ? `${url}/${routeUrl}` : url;
      const data = current.snapshot.routeConfig?.data as IRouteData | undefined;
      const breadcrumb = data?.breadcrumb;
      const breadcrumbIcon = data?.breadcrumbIcon;

      if (breadcrumb || breadcrumbIcon) {
        breadcrumbs.push({
          label: breadcrumb ? labels[breadcrumb] : undefined,
          icon: breadcrumbIcon,
          routerLink: url,
        });
      }

      current = current.firstChild;
    }

    return breadcrumbs;
  }
}
