import { ChangeDetectionStrategy, Component, inject, input, resource } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { FormControl, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { TranslatePipe } from '@ngx-translate/core';
import { ButtonModule } from 'primeng/button';
import { DatePickerModule } from 'primeng/datepicker';
import { IftaLabelModule } from 'primeng/iftalabel';
import { InputNumberModule } from 'primeng/inputnumber';
import { ToggleSwitchModule } from 'primeng/toggleswitch';
import { catchError, debounceTime, firstValueFrom, of, startWith } from 'rxjs';
import { ToastService } from 'src/app/core/services/toast.service';
import { ContainersApiService } from 'src/app/features/containers/containers-api.service';
import { IGetContainerLogsRequestBody } from 'src/app/features/containers/containers.interface';
import { BooleanFieldComponent } from 'src/app/shared/components/boolean-field/boolean-field.component';
import { TInterfaceToForm } from 'src/app/shared/types/interface-to-form.type';

@Component({
  selector: 'app-container-card-logs',
  imports: [
    InputNumberModule,
    ButtonModule,
    TranslatePipe,
    IftaLabelModule,
    ReactiveFormsModule,
    DatePickerModule,
    BooleanFieldComponent,
    ToggleSwitchModule,
  ],
  templateUrl: './container-card-logs.component.html',
  styleUrl: './container-card-logs.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ContainerCardLogsComponent {
  private readonly containersApiService = inject(ContainersApiService);
  private readonly toastService = inject(ToastService);

  public readonly hostId = input.required<number>();
  public readonly containerNameOrId = input.required<string>();

  protected readonly form = new FormGroup<TInterfaceToForm<IGetContainerLogsRequestBody>>({
    tail: new FormControl<number>(100),
    since: new FormControl<Date>(null),
    until: new FormControl<Date>(null),
    details: new FormControl<boolean>(false),
    timestamps: new FormControl<boolean>(false),
  });
  protected readonly body = toSignal(
    this.form.valueChanges.pipe(debounceTime(300), startWith(this.form.value)),
  );
  protected readonly logs = resource({
    params: () => {
      const hostId = this.hostId();
      const containerNameOrId = this.containerNameOrId();
      const body = this.body();
      return { hostId, containerNameOrId, body };
    },
    loader: (params) => {
      return firstValueFrom(
        this.containersApiService
          .logs(
            params.params.hostId,
            params.params.containerNameOrId,
            params.params.body as IGetContainerLogsRequestBody,
          )
          .pipe(
            catchError((error) => {
              this.toastService.error(error);
              return of(null);
            }),
          ),
      );
    },
  });
}
