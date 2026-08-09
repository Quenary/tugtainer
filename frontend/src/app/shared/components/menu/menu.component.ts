import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  linkedSignal,
} from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
import { finalize, map } from 'rxjs';
import { LogoComponent } from '../logo/logo.component';
import { TranslatePipe, TranslateService } from '@ngx-translate/core';
import { Router, RouterLink, RouterLinkActive } from '@angular/router';
import { ButtonModule } from 'primeng/button';
import { RippleModule } from 'primeng/ripple';
import { SelectModule } from 'primeng/select';
import { MenuModule } from 'primeng/menu';
import { AppStore } from 'src/app/app.store';
import { AuthApiService } from 'src/app/features/auth/auth-api.service';
import { HostsStore } from 'src/app/features/hosts/hosts.store';
import { BadgeModule } from 'primeng/badge';
import { supportedLocales } from 'src/app/app.consts';
import { localeLabels, TAppLang } from 'src/app/core/services/locale.service';

@Component({
  selector: 'app-menu',
  imports: [
    LogoComponent,
    TranslatePipe,
    ButtonModule,
    RouterLink,
    RouterLinkActive,
    RippleModule,
    SelectModule,
    MenuModule,
    RouterLink,
    BadgeModule,
  ],
  templateUrl: './menu.component.html',
  styleUrl: './menu.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: {
    '[class.narrow]': 'narrow()',
  },
})
export class MenuComponent {
  private readonly breakpointObserver = inject(BreakpointObserver);
  private readonly translateService = inject(TranslateService);
  protected readonly appStore = inject(AppStore);
  private readonly authApiService = inject(AuthApiService);
  private readonly router = inject(Router);
  protected readonly hostsStore = inject(HostsStore);

  private readonly _narrow = toSignal<boolean>(
    this.breakpointObserver
      .observe([Breakpoints.Handset, Breakpoints.Small])
      .pipe(map((result) => result.matches)),
  );
  protected readonly narrow = linkedSignal(this._narrow);

  private readonly generalTranslation = toSignal(
    this.translateService.stream('GENERAL'),
  );
  private readonly themesTranslation = toSignal(
    this.translateService.stream('THEMES'),
  );
  protected readonly themes = computed(() => {
    const general = this.generalTranslation();
    const t = this.themesTranslation();
    return [
      {
        value: 'AUTO',
        label: general['AUTO'],
        icon: 'pi pi-heart',
        command: () => {
          this.appStore.setTheme('AUTO');
        },
      },
      {
        value: 'LIGHT',
        label: t['LIGHT'],
        icon: 'pi pi-sun',
        command: () => {
          this.appStore.setTheme('LIGHT');
        },
      },
      {
        value: 'app-dark',
        label: t['DARK'],
        icon: 'pi pi-moon',
        command: () => {
          this.appStore.setTheme('DARK');
        },
      },
    ];
  });
  protected readonly selectedThemeLabel = computed(() => {
    const theme = this.appStore.theme();
    const general = this.generalTranslation();
    const themes = this.themesTranslation();
    if (theme === 'AUTO') {
      return general?.['AUTO'];
    }
    return themes?.[theme];
  });

  protected readonly languages = computed(() => {
    const general = this.generalTranslation();
    return [
      {
        value: 'AUTO' as TAppLang,
        label: general['AUTO'],
        icon: 'pi pi-globe',
        command: () => {
          this.appStore.setLang('AUTO');
        },
      },
      ...supportedLocales
        .map((code) => ({
          value: code,
          label: localeLabels[code],
          command: () => {
            this.appStore.setLang(code);
          },
        }))
        .sort((a, b) => a.value.localeCompare(b.value)),
    ];
  });
  protected readonly selectedLangLabel = computed(() => {
    const lang = this.appStore.lang();
    const general = this.generalTranslation();
    if (lang === 'AUTO') {
      return general?.['AUTO'];
    }
    return localeLabels[lang];
  });

  protected openRepo(): void {
    window.open('https://github.com/Quenary/tugtainer', '_blank');
  }

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
}
