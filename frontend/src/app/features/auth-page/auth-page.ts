import { ChangeDetectionStrategy, Component, inject, resource, signal } from '@angular/core';
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

  constructor() {
    // Check for OIDC auto-redirect when component initializes
    this.checkOidcAutoRedirect();
  }

  public readonly isLoading = signal<boolean>(false);
  public readonly isPasswordSet = resource({
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
  public readonly isOidcEnabled = resource({
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

  public readonly isPasswordEnabled = resource({
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

  public readonly isOidcAutoRedirectEnabled = resource({
    defaultValue: false,
    loader: () =>
      firstValueFrom(
        this.authApiService.isOidcAutoRedirectEnabled().pipe(
          retry(1),
          catchError((error) => {
            this.toastService.error(error);
            return throwError(() => error);
          }),
        ),
      ),
  });

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
      .login({}, { password })
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

  private checkOidcAutoRedirect(): void {
    // Wait for resources to load, then check if auto-redirect should happen
    setTimeout(() => {
      const oidcEnabled = this.isOidcEnabled.value();
      const passwordEnabled = this.isPasswordEnabled.value();
      const autoRedirectEnabled = this.isOidcAutoRedirectEnabled.value();

      // Auto-redirect if OIDC auto-redirect is enabled, OIDC is enabled, and password auth is disabled
      if (autoRedirectEnabled && oidcEnabled && !passwordEnabled) {
        this.authApiService.initiateLogin('oidc');
      }
    }, 100);
  }
}
