import { ComponentFixture, TestBed } from '@angular/core/testing';
import { InspectComponent } from './inspect.component';
import { ComponentRef } from '@angular/core';
import { provideTranslateService } from '@ngx-translate/core';
import { TreeNode } from 'primeng/api';
import { ResizeObserverMock } from '@testing/mocks/resize-observer.mock';

describe('InspectComponent', () => {
  let component: InspectComponent;
  let fixture: ComponentFixture<InspectComponent>;
  let componentRef: ComponentRef<InspectComponent>;

  const inspect = {
    'Id': 'a65cba45142fd3c9300de00e7628b10c72afa269dc2385412853589b095ec668',
    'Created': '2026-05-11T01:50:43.372359986Z',
    'Path': 'docker-entrypoint.sh',
    'Args': ['postgres'],
    'State': {
      'Status': 'running',
      'Running': true,
      'Paused': false,
    },
  };

  beforeEach(async () => {
    vi.stubGlobal('ResizeObserver', ResizeObserverMock);

    await TestBed.configureTestingModule({
      imports: [InspectComponent],
      providers: [provideTranslateService()],
    }).compileComponents();

    fixture = TestBed.createComponent(InspectComponent);
    component = fixture.componentInstance;
    componentRef = fixture.componentRef;
    componentRef.setInput('inspect', inspect);
  });

  it('should create', () => {
    fixture.detectChanges();
    expect(component).toBeTruthy();
  });

  it('should prepare tree', () => {
    const expected: TreeNode[] = [
      {
        'label':
          'Id: a65cba45142fd3c9300de00e7628b10c72afa269dc2385412853589b095ec668',
        'data':
          'a65cba45142fd3c9300de00e7628b10c72afa269dc2385412853589b095ec668',
        'leaf': true,
      },
      {
        'label': 'Created: 2026-05-11T01:50:43.372359986Z',
        'data': '2026-05-11T01:50:43.372359986Z',
        'leaf': true,
      },
      {
        'label': 'Path: docker-entrypoint.sh',
        'data': 'docker-entrypoint.sh',
        'leaf': true,
      },
      {
        'label': 'Args',
        'data': ['postgres'],
        'children': [
          {
            'label': '0: postgres',
            'data': 'postgres',
            'leaf': true,
          },
        ],
        'leaf': false,
      },
      {
        'label': 'State',
        'data': {
          'Status': 'running',
          'Running': true,
          'Paused': false,
        },
        'children': [
          {
            'label': 'Status: running',
            'data': 'running',
            'leaf': true,
          },
          {
            'label': 'Running: true',
            'data': true,
            'leaf': true,
          },
          {
            'label': 'Paused: false',
            'data': false,
            'leaf': true,
          },
        ],
        'leaf': false,
      },
    ];
    const res = component['inspectTree']();
    expect(expected.length).toEqual(res.length);
    expected.forEach((expected, index) => {
      expect(res[index]).toEqual(expect.objectContaining(expected));
    });
  });
});
