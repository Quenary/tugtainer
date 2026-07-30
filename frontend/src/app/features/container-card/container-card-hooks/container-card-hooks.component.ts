import {
  ChangeDetectionStrategy,
  Component,
  effect,
  input,
  output,
} from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { TranslatePipe } from '@ngx-translate/core';
import { ButtonModule } from 'primeng/button';
import { IftaLabelModule } from 'primeng/iftalabel';
import { TextareaModule } from 'primeng/textarea';
import { IContainerHooks } from 'src/app/features/containers/containers.interface';
import { TInterfaceToForm } from '@shared/types/interface-to-form.type';

type THookField = keyof IContainerHooks;

const HOOK_FIELDS: THookField[] = [
  'pre_update',
  'post_update',
  'pre_stop',
  'pre_rollback',
  'post_rollback',
];

@Component({
  selector: 'app-container-card-hooks',
  imports: [
    ReactiveFormsModule,
    TranslatePipe,
    IftaLabelModule,
    TextareaModule,
    ButtonModule,
  ],
  templateUrl: './container-card-hooks.component.html',
  styleUrl: './container-card-hooks.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ContainerCardHooksComponent {
  public readonly hooks = input<IContainerHooks | null>(null);
  public readonly save = output<IContainerHooks>();

  protected readonly HOOK_FIELDS = HOOK_FIELDS;

  protected readonly form = new FormGroup<
    TInterfaceToForm<Record<THookField, string>>
  >({
    pre_update: new FormControl<string>('', { nonNullable: true }),
    post_update: new FormControl<string>('', { nonNullable: true }),
    pre_stop: new FormControl<string>('', { nonNullable: true }),
    pre_rollback: new FormControl<string>('', { nonNullable: true }),
    post_rollback: new FormControl<string>('', { nonNullable: true }),
  });

  constructor() {
    effect(() => {
      const hooks = this.hooks();
      this.form.setValue(
        {
          pre_update: (hooks?.pre_update ?? []).join('\n'),
          post_update: (hooks?.post_update ?? []).join('\n'),
          pre_stop: (hooks?.pre_stop ?? []).join('\n'),
          pre_rollback: (hooks?.pre_rollback ?? []).join('\n'),
          post_rollback: (hooks?.post_rollback ?? []).join('\n'),
        },
        { emitEvent: false },
      );
    });
  }

  protected onSave(): void {
    const raw = this.form.getRawValue();
    const toLines = (value: string): string[] =>
      value
        .split('\n')
        .map((line) => line.trim())
        .filter((line) => line.length > 0);

    this.save.emit({
      pre_update: toLines(raw.pre_update),
      post_update: toLines(raw.post_update),
      pre_stop: toLines(raw.pre_stop),
      pre_rollback: toLines(raw.pre_rollback),
      post_rollback: toLines(raw.post_rollback),
    });
  }
}
