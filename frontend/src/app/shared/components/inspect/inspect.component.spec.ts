import { ComponentFixture, TestBed } from '@angular/core/testing';

import { InspectComponent } from './inspect.component';

describe('InspectComponent', () => {
  let component: InspectComponent;
  let fixture: ComponentFixture<InspectComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [InspectComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(InspectComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
