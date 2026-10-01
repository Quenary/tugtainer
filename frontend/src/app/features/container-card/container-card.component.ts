import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  OnDestroy,
  signal,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute } from '@angular/router';
import {
  EContainerHealthSeverity,
  EContainerStatusSeverity,
  IContainerHooks,
  IContainerPatchBody,
  TControlContainerCommand,
} from 'src/app/features/containers/containers.interface';
import {
  AccordionPanel,
  AccordionHeader,
  AccordionContent,
  Accordion,
} from '@openng/optimus-ui/accordion';
import { TranslatePipe } from '@ngx-translate/core';
import { IftaLabel } from '@openng/optimus-ui/iftalabel';
import { InputText } from '@openng/optimus-ui/inputtext';
import { InputNumber } from '@openng/optimus-ui/inputnumber';
import { IconField } from '@openng/optimus-ui/iconfield';
import { InputIcon } from '@openng/optimus-ui/inputicon';
import { Textarea } from '@openng/optimus-ui/textarea';
import { Toolbar } from '@openng/optimus-ui/toolbar';
import { Button } from '@openng/optimus-ui/button';
import { Tag } from '@openng/optimus-ui/tag';
import { Tooltip } from '@openng/optimus-ui/tooltip';
import { ContainerActionsComponent } from '@shared/components/container-actions/container-actions.component';
import { ToggleSwitch } from '@openng/optimus-ui/toggleswitch';
import { FormsModule } from '@angular/forms';
import { ContainerCardLogsComponent } from './container-card-logs/container-card-logs.component';
import { ContainerCardHooksComponent } from './container-card-hooks/container-card-hooks.component';
import { BooleanFieldComponent } from '@shared/components/boolean-field/boolean-field.component';
import { DayjsPipe } from '@shared/pipes/dayjs.pipe';
import { getImageSourceUrl } from '@shared/functions/get-image-source-url.function';
import { ContainersStore } from '../containers/containers.store';
import { InspectComponent } from '@shared/components/inspect/inspect.component';
import { SettingsStore } from '../settings/settings.store';
import { ESettingKey } from '../settings/settings.interface';
import { Divider } from '@openng/optimus-ui/divider';

@Component({
  selector: 'app-container-card',
  imports: [
    AccordionPanel,
    AccordionHeader,
    AccordionContent,
    Accordion,
    TranslatePipe,
    IftaLabel,
    InputText,
    InputNumber,
    IconField,
    InputIcon,
    Textarea,
    Toolbar,
    Button,
    Tag,
    Tooltip,
    ContainerActionsComponent,
    ToggleSwitch,
    FormsModule,
    ContainerCardLogsComponent,
    ContainerCardHooksComponent,
    BooleanFieldComponent,
    DayjsPipe,
    InspectComponent,
    Divider,
  ],
  templateUrl: './container-card.component.html',
  styleUrl: './container-card.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ContainerCardComponent implements OnDestroy {
  private readonly activatedRoute = inject(ActivatedRoute);
  protected readonly containersStore = inject(ContainersStore);
  private readonly settingsStore = inject(SettingsStore);

  protected readonly EContainerStatusSeverity = EContainerStatusSeverity;
  protected readonly EContainerHealthSeverity = EContainerHealthSeverity;

  /**
   * Value of opened accordion items
   */
  protected readonly accordionValue = signal<
    string | number | string[] | number[]
  >('general');
  /**
   * Ports value
   */
  protected readonly itemPorts = computed(() => {
    const item = this.containersStore.selected();
    let ports = '';
    if (item?.ports) {
      for (const [key, binds] of Object.entries(item.ports)) {
        for (const bind of binds) {
          ports += `${key}:`;
          if (bind.HostIp) {
            ports += `${bind.HostIp}:`;
          }
          ports += `${bind.HostPort}\n`;
        }
      }
    }
    return ports;
  });
  /**
   * Ports textarea rows count
   */
  protected readonly itemPortsRows = computed<number>(() => {
    const itemPorts = this.itemPorts();
    return itemPorts.split('\n').length;
  });
  /**
   * Container inspect object
   */
  protected readonly inspect = computed(
    () => this.containersStore.selectedInfo()?.inspect,
  );
  /**
   * Source repository URL from image labels, if the publisher set one.
   */
  protected readonly sourceUrl = computed(() =>
    getImageSourceUrl(this.inspect()),
  );
  /**
   * Reference of the image the container ran before its last update.
   * Prefers the digests, which are the only value that pins the exact
   * image again, and falls back to the tags for local images.
   */
  protected readonly previousImage = computed<string>(() => {
    const item = this.containersStore.selected();
    const digests = item?.previous_image_digests ?? [];
    const tags = item?.previous_image_tags ?? [];
    return (digests.length ? digests : tags).join('\n');
  });
  /**
   * Whether the card has derived fields to separate from the editable ones:
   * versions, check timestamps, and the previous image.
   */
  protected readonly hasComputedFields = computed(() => {
    const item = this.containersStore.selected();
    const previousImage = this.previousImage();
    if (!item) {
      return false;
    }
    return Boolean(
      item.current_version ||
      (item.update_available &&
        (item.available_version || item.available_created)) ||
      item.previous_image_version ||
      item.checked_at ||
      item.remote_digests_changed_at ||
      item.updated_at ||
      previousImage,
    );
  });
  /**
   * Previous image textarea rows count
   */
  protected readonly previousImageRows = computed<number>(() =>
    Math.max(this.previousImage().split('\n').length, 2),
  );
  /**
   * Placeholder showing the global DELAY_UPDATE_FOR value
   */
  protected readonly globalDelayPlaceholder = computed(() => {
    const settings = this.settingsStore.entityMap();
    const value = settings[ESettingKey.DELAY_UPDATE_FOR]?.value;
    return value === undefined || value === null ? '' : String(value);
  });
  /**
   * Placeholder showing the host's container_hc_timeout value
   */
  protected readonly globalHealthcheckTimeoutPlaceholder = computed(() => {
    const host = this.containersStore.host();
    const value = host?.container_hc_timeout;
    return value === undefined || value === null ? '' : String(value);
  });

  constructor() {
    this.activatedRoute.params
      .pipe(takeUntilDestroyed())
      .subscribe((params) => {
        this.containersStore.select(params['containerNameOrId']);
        this.containersStore.loadSelected();
      });
  }

  ngOnDestroy(): void {
    this.containersStore.select(null);
  }

  protected patchContainer(body: IContainerPatchBody): void {
    const c = this.containersStore.selected();
    this.containersStore.patchContainer({
      containerName: c.name,
      body,
    });
  }

  protected onDelayUpdateForChange(value: number | null): void {
    this.patchContainer({ delay_update_for: value ?? null });
  }

  protected onHealthcheckTimeoutChange(value: number | null): void {
    this.patchContainer({ healthcheck_timeout: value ?? null });
  }

  protected onCheck(): void {
    const c = this.containersStore.selected();
    this.containersStore.checkContainer({ containerName: c.name });
  }

  protected onUpdate(): void {
    const c = this.containersStore.selected();
    this.containersStore.updateContainer({ containerName: c.name });
  }

  protected onCommand(command: TControlContainerCommand): void {
    const c = this.containersStore.selected();
    this.containersStore.controlContainer({ containerName: c.name, command });
  }

  protected onSaveHooks(hooks: IContainerHooks): void {
    this.patchContainer({ hooks });
  }

  protected openSource(): void {
    const url = this.sourceUrl();
    if (url) {
      window.open(url, '_blank', 'noopener,noreferrer');
    }
  }
}
