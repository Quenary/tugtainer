import { ComponentFixture, TestBed } from '@angular/core/testing';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { MultiContainerActionsComponent } from './multi-container-actions.component';
import { EContainerStatus } from 'src/app/features/containers/containers.interface';
import { IContainerEntity } from 'src/app/features/containers/containers.store';
import { vi } from 'vitest';

const createContainer = (
  name: string,
  status: EContainerStatus,
  isProtected = false,
): IContainerEntity =>
  ({
    id: 1,
    host_id: 1,
    name,
    container_id: `id-${name}`,
    image: 'test:latest',
    status,
    protected: isProtected,
    check_enabled: true,
    update_enabled: true,
    update_available: false,
    ports: {},
    exit_code: 0,
    health: 'healthy',
    checked_at: '',
    updated_at: '',
    remote_digests_changed_at: null,
    delay_update_for: null,
    healthcheck_timeout: null,
    previous_image_digests: null,
    previous_image_tags: null,
    previous_image_version: null,
    current_version: null,
    created_at: '',
    modified_at: '',
    hooks: null,
    loading: null,
    progress: null,
  }) as IContainerEntity;

describe('MultiContainerActionsComponent', () => {
  let component: MultiContainerActionsComponent;
  let fixture: ComponentFixture<MultiContainerActionsComponent>;
  let translateService: TranslateService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MultiContainerActionsComponent, TranslateModule.forRoot()],
    }).compileComponents();

    translateService = TestBed.inject(TranslateService);
    translateService.setTranslation('en', {
      CONTAINERS: {
        COMMANDS: {
          START: 'Start',
          STOP: 'Stop',
          RESTART: 'Restart',
          KILL: 'Kill',
          PAUSE: 'Pause',
          UNPAUSE: 'Unpause',
        },
      },
    });
    translateService.use('en');

    fixture = TestBed.createComponent(MultiContainerActionsComponent);
    component = fixture.componentInstance;
  });

  it('should create and be disabled when no containers are provided', () => {
    fixture.detectChanges();
    expect(component).toBeTruthy();
    expect(component['isSplitButtonDisabled']()).toBe(true);
  });

  it('should select stop as majority action when only running containers are selected', () => {
    const c1 = createContainer('c1', EContainerStatus.running);
    const c2 = createContainer('c2', EContainerStatus.running);
    fixture.componentRef.setInput('containers', [c1, c2]);
    fixture.detectChanges();

    expect(component['majorityCommand']()).toBe('stop');
    expect(component['mainLabel']()).toBe('Stop (2)');
    expect(component['isSplitButtonDisabled']()).toBe(false);

    const items = component['menuItems']();
    const startItem = items.find((i) => i.label?.startsWith('Start'));
    const restartItem = items.find((i) => i.label?.startsWith('Restart'));

    expect(startItem?.disabled).toBe(true);
    expect(restartItem?.disabled).toBe(false);
    expect(restartItem?.label).toBe('Restart (2)');
  });

  it('should select restart as majority action when mixed running and exited containers are selected', () => {
    const c1 = createContainer('c1', EContainerStatus.running);
    const c2 = createContainer('c2', EContainerStatus.running);
    const c3 = createContainer('c3', EContainerStatus.exited);
    const c4 = createContainer('c4', EContainerStatus.exited);
    const c5 = createContainer('c5', EContainerStatus.exited);

    fixture.componentRef.setInput('containers', [c1, c2, c3, c4, c5]);
    fixture.detectChanges();

    // Restart is applicable to all 5 (exited + running)
    expect(component['majorityCommand']()).toBe('restart');
    expect(component['mainLabel']()).toBe('Restart (5)');

    const items = component['menuItems']();
    const startItem = items.find((i) => i.label?.startsWith('Start'));
    const stopItem = items.find((i) => i.label?.startsWith('Stop'));
    const unpauseItem = items.find((i) => i.label?.startsWith('Unpause'));

    expect(startItem?.disabled).toBe(false);
    expect(startItem?.label).toBe('Start (3)');
    expect(stopItem?.disabled).toBe(false);
    expect(stopItem?.label).toBe('Stop (2)');
    expect(unpauseItem?.disabled).toBe(true);
  });

  it('should exclude protected containers from action targets', () => {
    const c1 = createContainer('c1', EContainerStatus.running, false);
    const c2 = createContainer('c2', EContainerStatus.running, true); // protected

    fixture.componentRef.setInput('containers', [c1, c2]);
    fixture.detectChanges();

    expect(component['targetMap']().stop).toEqual([c1]);
    expect(component['mainLabel']()).toBe('Stop (1)');
  });

  it('should emit onCommand when main button is clicked', () => {
    const c1 = createContainer('c1', EContainerStatus.exited);
    const emitSpy = vi.fn();
    component.OnCommand.subscribe(emitSpy);

    fixture.componentRef.setInput('containers', [c1]);
    fixture.detectChanges();

    component['onMainButtonClick']();

    expect(emitSpy).toHaveBeenCalledWith({
      command: 'start',
      containers: [c1],
    });
  });

  it('should emit onCommand when a dropdown menu item is invoked', () => {
    const c1 = createContainer('c1', EContainerStatus.running);
    const c2 = createContainer('c2', EContainerStatus.exited);
    const emitSpy = vi.fn();
    component.OnCommand.subscribe(emitSpy);

    fixture.componentRef.setInput('containers', [c1, c2]);
    fixture.detectChanges();

    // majority is restart (2), start has 1 (c2)
    const items = component['menuItems']();
    const startItem = items.find((i) => i.label?.startsWith('Start'));
    expect(startItem).toBeDefined();

    startItem!.command!({ item: startItem });

    expect(emitSpy).toHaveBeenCalledWith({
      command: 'start',
      containers: [c2],
    });
  });
});
