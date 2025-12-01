import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ContainerActions } from './container-actions';

describe('ContainerActions', () => {
  let component: ContainerActions;
  let fixture: ComponentFixture<ContainerActions>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ContainerActions]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ContainerActions);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
