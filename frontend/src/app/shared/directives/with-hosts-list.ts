import { computed, Directive, effect, inject, model, resource, signal } from '@angular/core';
import { firstValueFrom, catchError, of } from 'rxjs';
import { ToastService } from 'src/app/core/services/toast.service';
import { HostsApiService } from 'src/app/entities/hosts/hosts-api.service';
import { IHostInfo } from 'src/app/entities/hosts/hosts-interface';

/**
 * Common directive for containers/images pages
 */
@Directive({
  selector: '[withHostsList]',
})
export class WithHostsList {
  protected readonly hostsApiService = inject(HostsApiService);
  protected readonly toastService = inject(ToastService);

  /**
   * Key of accordion items value in storage
   */
  public readonly accordionValueStorageKey = model<string>();

  /**
   * Icon for collapse all button
   */
  protected readonly collapseAllIcon = computed<string>(() => {
    const accordionValue = this.accordionValue();
    return Array.isArray(accordionValue) && accordionValue.length
      ? 'pi pi-angle-double-up'
      : 'pi pi-angle-double-down';
  });

  /**
   * Hosts list
   */
  protected readonly hosts = resource<IHostInfo[], {}>({
    loader: () =>
      firstValueFrom(
        this.hostsApiService.list().pipe(
          catchError((error) => {
            this.toastService.error(error);
            return of([]);
          }),
        ),
      ),
  });
  /**
   * Accordion items value
   */
  protected readonly accordionValue = signal<string | number | string[] | number[]>(undefined);

  constructor() {
    // Save accordion value to storage
    effect(() => {
      const accordionValueStorageKey = this.accordionValueStorageKey();
      const accordionValue = this.accordionValue();
      if (accordionValueStorageKey && accordionValue) {
        localStorage.setItemJson(accordionValueStorageKey, accordionValue);
      }
    });
    // Set accordion value from storage
    effect(() => {
      const accordionValueStorageKey = this.accordionValueStorageKey();
      if (accordionValueStorageKey) {
        this.accordionValue.set(localStorage.getItemJson(accordionValueStorageKey));
      }
    });
    // Set accordion value if nothing in storage
    const initAccordionValue = effect(
      () => {
        const hostsHasValue = this.hosts.hasValue();
        const accordionValue = this.accordionValue();
        if (hostsHasValue) {
          if (!accordionValue) {
            const hosts = this.hosts.value();
            this.accordionValue.set(hosts.filter((h) => h.enabled).map((h) => h.id));
          }
          initAccordionValue.destroy();
        }
      },
      {
        manualCleanup: true,
      },
    );
  }

  /**
   * Toggle accordion items
   */
  protected toggleCollapseAll(): void {
    const accordionValue = (this.accordionValue() as number[]) ?? [];
    const hosts = this.hosts.value() ?? [];
    if (accordionValue.length) {
      this.accordionValue.set([]);
    } else {
      this.accordionValue.set(hosts.filter((item) => item.enabled).map((item) => item.id));
    }
  }
}
