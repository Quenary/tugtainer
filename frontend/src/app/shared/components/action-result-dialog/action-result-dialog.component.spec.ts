import { ComponentFixture, TestBed } from '@angular/core/testing';

import {
  ActionResultDialogComponent,
  IActionResultDialogData,
} from './action-result-dialog.component';
import { DynamicDialogConfig } from 'primeng/dynamicdialog';
import { By } from '@angular/platform-browser';
import { HostCheckResultComponent } from '../host-check-result/host-check-result.component';

describe('ActionResultDialogComponent', () => {
  let component: ActionResultDialogComponent;
  let fixture: ComponentFixture<ActionResultDialogComponent>;

  let dynamicDialogConfigMock: DynamicDialogConfig<IActionResultDialogData>;

  beforeEach(async () => {
    dynamicDialogConfigMock = {
      data: {
        results: [
          {
            host_id: 1,
            host_name: 'test',
            items: [],
            prune_result: '',
          },
        ],
        pruneResult: 'test',
      },
    };

    await TestBed.configureTestingModule({
      imports: [ActionResultDialogComponent],
      providers: [
        { provide: DynamicDialogConfig, useValue: dynamicDialogConfigMock },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(ActionResultDialogComponent);
    component = fixture.componentInstance;
  });

  it('should create', () => {
    fixture.detectChanges();
    expect(component).toBeTruthy();
    expect(
      fixture.debugElement.query(By.directive(HostCheckResultComponent)),
    ).toBeTruthy();
    expect(fixture.debugElement.query(By.css('pre'))).toBeTruthy();
  });
});
