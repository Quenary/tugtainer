import { ComponentFixture, TestBed } from '@angular/core/testing';
import { signal } from '@angular/core';

import {
  JobsProgressDialogComponent,
  IJobsProgressDialogSource,
  toJobsProgressDialogData,
} from './jobs-progress-dialog.component';
import { DynamicDialogConfig } from 'primeng/dynamicdialog';
import { By } from '@angular/platform-browser';
import { HostJobsResultComponent } from '../host-jobs-result/host-jobs-result.component';
import { provideTranslateService } from '@ngx-translate/core';
import { EJobStatus, IHostState } from '@shared/interfaces/jobs.interface';

describe('JobsProgressDialogComponent', () => {
  let component: JobsProgressDialogComponent;
  let fixture: ComponentFixture<JobsProgressDialogComponent>;
  let source: ReturnType<
    typeof signal<{
      jobState?: IHostState | null;
      pruneResult?: string | null;
    }>
  >;
  let dynamicDialogConfigMock: DynamicDialogConfig<IJobsProgressDialogSource>;

  beforeEach(async () => {
    source = signal({
      jobState: {
        status: EJobStatus.CHECKING,
        current: {
          kind: 'check' as const,
          names: ['a'],
          status: EJobStatus.CHECKING,
          host_name: 'test',
          containers: {
            a: { status: EJobStatus.CHECKING },
          },
        },
        queued: [{ kind: 'update' as const, names: ['c', 'd'] }],
        completed: [
          {
            kind: 'check' as const,
            names: ['x'],
            status: EJobStatus.DONE,
            host_id: 1,
            host_name: 'test',
            containers: {},
          },
        ],
      },
      pruneResult: 'test',
    });
    dynamicDialogConfigMock = {
      data: {
        read: () => source(),
      },
    };

    await TestBed.configureTestingModule({
      imports: [JobsProgressDialogComponent],
      providers: [
        { provide: DynamicDialogConfig, useValue: dynamicDialogConfigMock },
        provideTranslateService(),
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(JobsProgressDialogComponent);
    component = fixture.componentInstance;
  });

  it('should create', () => {
    fixture.detectChanges();
    expect(component).toBeTruthy();
    expect(fixture.debugElement.query(By.css('p-accordion'))).toBeTruthy();
    expect(fixture.debugElement.query(By.css('pre'))).toBeTruthy();
    expect(fixture.nativeElement.textContent).toContain('c, d');
  });

  it('updates when the store source changes', () => {
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('c, d');

    source.set({
      jobState: {
        status: EJobStatus.DONE,
        completed: [
          {
            kind: 'update',
            names: ['new-container'],
            status: EJobStatus.DONE,
            host_name: 'test',
            containers: {},
          },
        ],
      },
      pruneResult: null,
    });
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('new-container');
    expect(fixture.nativeElement.textContent).not.toContain('c, d');
  });

  it('renders job results inside accordion content', () => {
    fixture.detectChanges();
    const result = fixture.debugElement.query(
      By.directive(HostJobsResultComponent),
    );
    expect(result).toBeTruthy();
    expect(
      result.nativeElement.closest('.p-accordioncontent, p-accordion-content'),
    ).toBeTruthy();
  });
});

describe('toJobsProgressDialogData', () => {
  it('keeps every completed job', () => {
    const fromHistory = toJobsProgressDialogData(
      {
        status: EJobStatus.DONE,
        completed: [
          { kind: 'check', names: ['a', 'b'], status: EJobStatus.DONE },
          { kind: 'update', names: ['c', 'd'], status: EJobStatus.DONE },
        ],
      },
      null,
    );
    expect(fromHistory.completed).toHaveLength(2);
  });
});
