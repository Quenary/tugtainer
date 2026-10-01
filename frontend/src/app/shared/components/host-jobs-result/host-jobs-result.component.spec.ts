import { ComponentFixture, TestBed } from '@angular/core/testing';
import { EJobStatus, IJob } from '@shared/interfaces/jobs.interface';
import {
  IContainerJobResult,
  IServiceJobResult,
} from '@shared/interfaces/jobs-result.interface';
import { HostJobsResultComponent } from './host-jobs-result.component';

describe('HostJobsResultComponent', () => {
  let fixture: ComponentFixture<HostJobsResultComponent>;
  let component: HostJobsResultComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [HostJobsResultComponent],
    })
      .overrideComponent(HostJobsResultComponent, {
        set: { template: '' },
      })
      .compileComponents();

    fixture = TestBed.createComponent(HostJobsResultComponent);
    component = fixture.componentInstance;
  });

  describe('items', () => {
    function itemsFor(job: IJob) {
      fixture.componentRef.setInput('job', job);
      return component['items']();
    }

    it('uses the container name and id', () => {
      expect(
        itemsFor({
          containers: {
            'slot-nginx': {
              status: EJobStatus.DONE,
              result: {
                container: { Name: 'nginx', Id: 'abc' },
                result: 'updated',
              } as IContainerJobResult,
            },
          },
        }),
      ).toEqual([
        { id: 'abc', name: 'nginx', result: 'updated', severity: 'info' },
      ]);
    });

    it('uses the service id when it is present', () => {
      expect(
        itemsFor({
          containers: {
            'slot-api': {
              status: EJobStatus.DONE,
              result: {
                service_name: 'api',
                service_id: 'svc-1',
                result: 'failed',
              } as IServiceJobResult,
            },
          },
        }),
      ).toEqual([
        { id: 'svc-1', name: 'api', result: 'failed', severity: 'danger' },
      ]);
    });

    it('falls back to the service name without an id', () => {
      expect(
        itemsFor({
          containers: {
            'slot-worker': {
              status: EJobStatus.DONE,
              result: {
                service_name: 'worker',
                result: 'rolled_back',
              } as IServiceJobResult,
            },
          },
        }),
      ).toEqual([
        {
          id: 'worker',
          name: 'worker',
          result: 'rolled_back',
          severity: 'warn',
        },
      ]);
    });

    it('skips a slot without a result', () => {
      expect(
        itemsFor({
          containers: {
            'slot-empty': { status: EJobStatus.DONE },
          },
        }),
      ).toEqual([]);
    });

    it('keeps a pending outcome with a contrast tag', () => {
      expect(
        itemsFor({
          containers: {
            'slot-pending': {
              status: EJobStatus.DONE,
              result: { result: null } as IContainerJobResult,
            },
          },
        }),
      ).toEqual([
        {
          id: 'slot-pending',
          name: 'slot-pending',
          result: null,
          severity: 'contrast',
        },
      ]);
    });
  });
});
