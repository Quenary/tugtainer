import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ContainerCard } from './container-card';

describe('ContainerCard', () => {
  let component: ContainerCard;
  let fixture: ComponentFixture<ContainerCard>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ContainerCard]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ContainerCard);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
