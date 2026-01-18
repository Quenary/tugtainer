import {
  ChangeDetectionStrategy,
  Component,
  effect,
  inject,
  resource,
  signal,
} from '@angular/core';
import { Router } from '@angular/router';
import { catchError, finalize, firstValueFrom, retry, throwError } from 'rxjs';
import { AuthApiService } from 'src/app/entities/auth/auth-api.service';
import { ISetPasswordBody } from 'src/app/entities/auth/auth-interface';
import { NewPasswordForm } from 'src/app/shared/components/new-password-form/new-password-form';
import { LoginForm } from './login-form/login-form';
import { Logo } from 'src/app/shared/components/logo/logo';
import { ToastService } from 'src/app/core/services/toast.service';
import { ButtonModule } from 'primeng/button';
import { DividerModule } from 'primeng/divider';
import { TranslatePipe } from '@ngx-translate/core';

@Component({
  selector: 'app-auth',
  imports: [NewPasswordForm, LoginForm, Logo, ButtonModule, DividerModule, TranslatePipe],
  templateUrl: './auth-page.html',
  styleUrl: './auth-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AuthPage {
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

  constructor() {
    effect(() => {
      const isDisabled = this.isAuthDisabled.value();
      if (isDisabled) {
        this.router.navigate(['/containers']);
      }
    });
  }

  onSubmitNewPassword($event: ISetPasswordBody): void {
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

  onSubmitLogin(password: string): void {
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

  onOidcLogin(): void {
    this.authApiService.initiateLogin('oidc');
  }
}
