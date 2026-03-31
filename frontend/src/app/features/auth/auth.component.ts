import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  inject,
  resource,
  signal,
} from '@angular/core';
import { Router } from '@angular/router';
import { catchError, finalize, firstValueFrom, retry, throwError } from 'rxjs';
import { AuthApiService } from 'src/app/features/auth/auth-api.service';
import { ISetPasswordBody } from 'src/app/features/auth/auth.interface';
import { NewPasswordFormComponent } from '@shared/components/new-password-form/new-password-form.component';
import { AuthFormComponent } from './auth-form/auth-form.component';
import { LogoComponent } from '@shared/components/logo/logo.component';
import { ToastService } from 'src/app/core/services/toast.service';
import { ButtonModule } from 'primeng/button';
import { DividerModule } from 'primeng/divider';
import { TranslatePipe } from '@ngx-translate/core';

@Component({
  selector: 'app-auth',
  imports: [
    NewPasswordFormComponent,
    AuthFormComponent,
    LogoComponent,
    ButtonModule,
    DividerModule,
    TranslatePipe,
    DividerModule,
  ],
  templateUrl: './auth.component.html',
  styleUrl: './auth.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AuthComponent {
  private readonly authApiService = inject(AuthApiService);
  private readonly router = inject(Router);
  private readonly toastService = inject(ToastService);

  protected readonly isLoading = signal<boolean>(false);
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
  /**
   * Is password set
   */
  protected readonly isPasswordSet = resource({
    defaultValue: false,
    loader: () =>
      firstValueFrom(
        this.authApiService.isPasswordSet().pipe(
          retry(1),
          catchError((error) => {
            this.toastService.error(error);
            return throwError(() => error);
          }),
        ),
      ),
  });
  /**
   * Is OIDC auth enabled
   */
  protected readonly isOidcEnabled = resource({
    defaultValue: false,
    loader: () =>
      firstValueFrom(
        this.authApiService.isAuthProviderEnabled('oidc').pipe(
          retry(1),
          catchError((error) => {
            this.toastService.error(error);
            return throwError(() => error);
          }),
        ),
      ),
  });
  /**
   * Is password auth enabled
   */
  protected readonly isPasswordEnabled = resource({
    defaultValue: false,
    loader: () =>
      firstValueFrom(
        this.authApiService.isAuthProviderEnabled('password').pipe(
          retry(1),
          catchError((error) => {
            this.toastService.error(error);
            return throwError(() => error);
          }),
        ),
      ),
  });
  /**
   * Whether to show divider
   */
  protected readonly showDivider = computed(() => {
    const isPasswordEnabled = this.isPasswordEnabled.value();
    const isOidcEnabled = this.isOidcEnabled.value();
    return isPasswordEnabled && isOidcEnabled;
  });

  constructor() {
    effect(() => {
      const isDisabled = this.isAuthDisabled.value();
      if (isDisabled) {
        this.router.navigate(['/containers']);
      }
    });
  }

  protected onSubmitNewPassword($event: ISetPasswordBody): void {
    this.isLoading.set(true);
    this.authApiService
      .setPassword($event)
      .pipe(finalize(() => this.isLoading.set(false)))
      .subscribe({
        next: () => {
          this.toastService.success();
          this.isPasswordSet.reload();
        },
        error: (error) => {
          this.toastService.error(error);
        },
      });
  }

  protected onSubmitLogin(password: string): void {
    this.isLoading.set(true);
    this.authApiService
      .login('password', { password }, {})
      .pipe(finalize(() => this.isLoading.set(false)))
      .subscribe({
        next: () => {
          this.router.navigate(['/containers']);
        },
        error: (error) => {
          this.toastService.error(error);
        },
      });
  }

  protected onOidcLogin(): void {
    this.authApiService.initiateLogin('oidc');
  }
}
