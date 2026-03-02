import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ContainerCardComponent } from './container-card.component';

describe('ContainerCard', () => {
  let component: ContainerCardComponent;
  let fixture: ComponentFixture<ContainerCardComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ContainerCardComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(ContainerCardComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
