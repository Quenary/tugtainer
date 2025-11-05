import { ChangeDetectionStrategy, Component, inject, OnInit, signal } from '@angular/core';
import { Router } from '@angular/router';
import { finalize } from 'rxjs';
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
export class AuthPage implements OnInit {
  private readonly authApiService = inject(AuthApiService);
  private readonly router = inject(Router);
  private readonly toastService = inject(ToastService);

  public readonly isLoading = signal<boolean>(false);
  public readonly isPasswordSet = signal<boolean>(null);
  public readonly isOidcEnabled = signal<boolean>(false);

  ngOnInit(): void {
    this.updateIsPasswordSet();
    this.updateIsOidcEnabled();
  }

  private updateIsPasswordSet(): void {
    this.isLoading.set(true);
    this.authApiService
      .isPasswordSet()
      .pipe(finalize(() => this.isLoading.set(false)))
      .subscribe({
        next: (res) => {
          this.isPasswordSet.set(res);
        },
        error: (error) => {
          this.toastService.error(error);
        },
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
          this.updateIsPasswordSet();
        },
        error: (error) => {
          this.toastService.error(error);
        },
      });
  }

  onSubmitLogin(password: string): void {
    this.isLoading.set(true);
    this.authApiService
      .login(password)
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

  private updateIsOidcEnabled(): void {
    this.authApiService.isOidcEnabled().subscribe({
      next: (res) => {
        this.isOidcEnabled.set(res);
      },
      error: (error) => {
        console.warn('Could not check OIDC status:', error);
        this.isOidcEnabled.set(false);
      },
    });
  }

  onOidcLogin(): void {
    this.authApiService.initiateOidcLogin();
  }
}
